import assert from 'node:assert/strict';
import { test } from 'node:test';
import { setTimeout as delay } from 'node:timers/promises';
import { request as httpRequest } from 'node:http';
import { createBaseballServer } from '../server.mjs';
import { runJsonCommand, boundedResponseJson, requestWork } from '../runtime-safety.mjs';
import { metricCatalog } from '../query-builder/metric-suite-query-builder.js';

const run = (code, options={}) => runJsonCommand(process.execPath, ['-e',code], {input:{safe:true},...options});
const request = { method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({metricId:'tfs'}) };
const result = {metric:{metricId:'tfs',status:'unavailable',value:null,gaps:[]},execution:'materialized-sql'};

async function withServer(options, work) {
  const server=createBaseballServer(options);
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  try { await work(`http://127.0.0.1:${server.address().port}`,server); }
  finally { server.abortWork(); server.closeAllConnections(); await new Promise(resolve=>server.close(resolve)); }
}

test('worker passes structured JSON and preserves exact strings', async()=>{
  const value=await run("process.stdin.resume();process.stdin.on('end',()=>process.stdout.write(JSON.stringify({value:'9007199254740993'})))");
  assert.equal(value.value,'9007199254740993');
});

test('hung worker is killed before its request is released', async()=>{
  const start=Date.now();
  await assert.rejects(run('setInterval(()=>{},1000)',{timeoutMs:150}),error=>error.code==='worker-timeout');
  assert.ok(Date.now()-start<5000);
});

test('cancelled worker is killed and returns the cancellation reason', async()=>{
  const controller=new AbortController();
  const pending=run('setInterval(()=>{},1000)',{signal:controller.signal});
  controller.abort(new DOMException('gone','AbortError'));
  await assert.rejects(pending,error=>error.name==='AbortError');
});

test('stdout and stderr limits terminate a worker without returning its diagnostics', async()=>{
  for(const [stream,code] of [['stdout','worker-output-limit'],['stderr','worker-error-limit']]) {
    await assert.rejects(run(`process.${stream}.write('sensitive-path'.repeat(1000));setInterval(()=>{},1000)`,
      {stdoutLimit:100,stderrLimit:100}),error=>error.code===code&&!error.message.includes('sensitive-path'));
  }
});

test('failed and malformed workers produce controlled errors', async()=>{
  await assert.rejects(run("process.stdout.write('{bad');"),error=>error.code==='invalid-worker-response');
  await assert.rejects(run("process.stderr.write('private credential');process.exit(2)"),error=>error.status===503&&!error.message.includes('credential'));
});

test('upstream body size is bounded while streaming', async()=>{
  assert.deepEqual(await boundedResponseJson(new Response('{"a":1}'),32),{a:1});
  await assert.rejects(boundedResponseJson(new Response('x'.repeat(1000)),32),error=>error.code==='upstream-response-limit');
  await assert.rejects(boundedResponseJson(new Response('<private error>')),error=>error.code==='invalid-upstream-response');
});

test('foreign hosts, origins and cross-site browsers cannot reach queries', async()=>{
  let calls=0;
  await withServer({servingExecutor:async()=>{calls++;return result;}},async url=>{
    for(const headers of [{Host:'attacker.example'},{Origin:'https://attacker.example'},{Origin:'null'},{'Sec-Fetch-Site':'cross-site'}]) {
      // Native HTTP preserves attack headers instead of fetch rewriting them.
      const status=await new Promise((resolve,reject)=>{
        const call=httpRequest(url+'/api/metrics/query',{method:'POST',headers:{...request.headers,...headers}},response=>{
          response.resume();response.on('end',()=>resolve(response.statusCode));
        });
        call.on('error',reject);call.end(request.body);
      });
      assert.equal(status,403,JSON.stringify(headers));
    }
    assert.equal(calls,0);
    assert.equal((await fetch(url+'/api/metrics/query',{...request,headers:{...request.headers,Origin:url}})).status,200);
  });
});

test('oversized and malformed bodies are rejected before query execution', async()=>{
  let calls=0;
  await withServer({servingExecutor:async()=>{calls++;return result;}},async url=>{
    assert.equal((await fetch(url+'/api/metrics/query',{...request,body:'x'.repeat(65*1024)})).status,413);
    assert.equal((await fetch(url+'/api/metrics/query',{...request,body:'{'})).status,400);
    const chunkedStatus = await new Promise((resolve,reject)=>{
      const call=httpRequest(url+'/api/metrics/query',{method:'POST',headers:{'Transfer-Encoding':'chunked'}},response=>{
        response.resume();response.on('end',()=>resolve(response.statusCode));
      });
      call.on('error',reject);call.write('x'.repeat(33*1024));call.end('x'.repeat(33*1024));
    });
    assert.equal(chunkedStatus,413);
    assert.equal(calls,0);
  });
});

test('overload rejects excess work while static pages and liveness remain available', async()=>{
  let release,started;
  const entered=new Promise(resolve=>{started=resolve;});
  await withServer({requestLimits:{maxActive:1},servingExecutor:async()=>{started();await new Promise(resolve=>{release=resolve;});return result;}},async url=>{
    const first=fetch(url+'/api/metrics/query',request);
    await entered;
    const busy=await fetch(url+'/api/metrics/query',request);
    assert.equal(busy.status,503); assert.equal(busy.headers.get('retry-after'),'2');
    assert.equal((await fetch(url+'/health/ready')).status,503);
    const normalizedStatus=await new Promise((resolve,reject)=>{
      const call=httpRequest(url,{path:'/./api/metrics/query',method:'POST'},response=>{
        response.resume();response.on('end',()=>resolve(response.statusCode));
      });
      call.on('error',reject);call.end(request.body);
    });
    assert.equal(normalizedStatus,503);
    assert.equal((await fetch(url+'/health/live')).status,200);
    assert.equal((await fetch(url+'/metrics')).status,200);
    release(); assert.equal((await first).status,200);
  });
});

test('readiness requires all metric identities in nonempty materialized serving, separately from metric coverage', async()=>{
  const metrics=(await metricCatalog()).metrics.map(metric=>({metricId:metric.id,status:'unavailable'}));
  metrics[0].status='available';
  await withServer({servingExecutor:async input=>{
    assert.equal(input.route,'metric-suite');assert.equal(input.view,'dashboard');
    return {execution:'materialized-sql',graphCount:15,metrics};
  }},async url=>{
    const response=await fetch(url+'/health/ready');
    assert.equal(response.status,200);
    const payload=await response.json();
    assert.equal(payload.metricsWithScopedResults,1);assert.equal(payload.metricCoverageIsSeparate,true);
    assert.equal((await (await fetch(url+'/health/live')).json()).nodeVersion,process.version);
  });
});

test('launcher identity stays available without graph or SQL dependencies', async()=>{
  let calls=0;
  const unavailable=async()=>{calls++;throw Error('Dependency unavailable');};
  await withServer({servingExecutor:unavailable,fetchImpl:unavailable},async url=>{
    const response=await fetch(url+'/health/live');
    assert.equal(response.status,200);
    const identity=await response.json();
    assert.equal(identity.service,'baseballo-explorer');
    assert.equal(identity.processId,process.pid);
    assert.equal(identity.nodeVersion,process.version);
    assert.match(identity.explorerSourceFingerprint,/^[0-9a-f]{64}$/);
    assert.equal(calls,0);
  });
});

test('readiness fails closed for stale, empty or incomplete serving and never falls back to RDF', async()=>{
  const metrics=(await metricCatalog()).metrics.map(metric=>({metricId:metric.id,status:'available'}));
  for(const output of [null,{graphCount:0,metrics},{graphCount:1,metrics:metrics.slice(1)},
    {graphCount:1,metrics:metrics.map(()=>metrics[0])},{metrics}]) {
    let graphRequests=0;
    await withServer({servingExecutor:async()=>{
      if(!output)throw Error('Stale serving');
      return {execution:'materialized-sql',...output};
    },fetchImpl:async()=>{graphRequests++;throw Error('Must not fall back');}},async url=>{
      const response=await fetch(url+'/health/ready');
      assert.equal(response.status,503);
      assert.equal(graphRequests,0);
    });
  }
});

test('request deadline aborts backend work and returns a controlled timeout', async()=>{
  let cancelled=false;
  await withServer({requestLimits:{deadlineMs:100},servingExecutor:async()=>{
    const signal=requestWork.getStore().signal;
    await new Promise((resolve,reject)=>signal.addEventListener('abort',()=>{cancelled=true;reject(signal.reason);},{once:true}));
  }},async url=>{
    const response=await fetch(url+'/api/metrics/query',request);
    assert.equal(response.status,504); assert.equal(cancelled,true);
  });
});

test('client disconnect propagates cancellation and releases the query slot', async()=>{
  let started,resolveCancelled,calls=0;
  const entered=new Promise(resolve=>{started=resolve;});
  const cancelled=new Promise(resolve=>{resolveCancelled=resolve;});
  await withServer({requestLimits:{maxActive:1},servingExecutor:async()=>{
    if(++calls>1)return result;
    const signal=requestWork.getStore().signal;started();
    await new Promise((resolve,reject)=>signal.addEventListener('abort',()=>{resolveCancelled();reject(signal.reason);},{once:true}));
  }},async url=>{
    const controller=new AbortController();
    const pending=fetch(url+'/api/metrics/query',{...request,signal:controller.signal});
    const rejection=assert.rejects(pending,error=>error.name==='AbortError');
    await entered;controller.abort();await rejection;
    await Promise.race([cancelled,delay(2000).then(()=>{throw Error('No backend cancellation');})]);
    await delay(20);
    assert.equal((await fetch(url+'/api/metrics/query',request)).status,200);
  });
});
