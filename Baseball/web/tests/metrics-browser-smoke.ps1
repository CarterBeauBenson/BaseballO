[CmdletBinding()]
param(
    [string] $BrowserPath = 'C:\Program Files\Google\Chrome\Application\chrome.exe',
    [string] $BaseUrl = 'http://127.0.0.1:4173',
    [string] $RunDepthProof
)
# Focused Windows UI regression; isolated headless profile, no browser packages.
# Uses the running Explorer and the previously verified August 25 example.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$profileDirectory = Join-Path ([IO.Path]::GetTempPath()) ('baseballo-metric-browser-' + [guid]::NewGuid().ToString('N'))
$desktopCapture = Join-Path $profileDirectory 'desktop.png'
$mobileCapture = Join-Path $profileDirectory 'mobile.png'
$browserProcess = Start-Process -FilePath $BrowserPath -WindowStyle Hidden -PassThru -ArgumentList @(
    '--headless=new', '--disable-gpu', '--no-first-run', '--remote-debugging-port=0',
    "--user-data-dir=`"$profileDirectory`"", 'about:blank'
)
$socket = [Net.WebSockets.ClientWebSocket]::new()
$script:commandId = 0
function Invoke-Cdp {
    param([string] $Method, [hashtable] $Parameters = @{})
    $script:commandId++
    $number = $script:commandId
    $serialized = @{ id=$number; method=$Method; params=$Parameters } | ConvertTo-Json -Depth 30 -Compress
    $bytes = [Text.Encoding]::UTF8.GetBytes($serialized)
    $tokenSource = [Threading.CancellationTokenSource]::new(45000)
    try {
        $null = $socket.SendAsync([ArraySegment[byte]]::new($bytes), [Net.WebSockets.WebSocketMessageType]::Text,
            $true, $tokenSource.Token).GetAwaiter().GetResult()
        do {
            $stream = [IO.MemoryStream]::new()
            try {
                do {
                    $buffer = [byte[]]::new(65536)
                    $received = $socket.ReceiveAsync([ArraySegment[byte]]::new($buffer), $tokenSource.Token).GetAwaiter().GetResult()
                    if ($received.MessageType -eq [Net.WebSockets.WebSocketMessageType]::Close) { throw 'Browser connection closed.' }
                    $stream.Write($buffer, 0, $received.Count)
                } until ($received.EndOfMessage)
                $message = [Text.Encoding]::UTF8.GetString($stream.ToArray()) | ConvertFrom-Json
            } finally { $stream.Dispose() }
        } until ($message.PSObject.Properties['id'] -and $message.id -eq $number)
        if ($message.PSObject.Properties['error']) { throw ($message.error | ConvertTo-Json -Compress) }
        return $message.result
    } finally { $tokenSource.Dispose() }
}
function Invoke-Page {
    param([string] $Expression)
    $result = Invoke-Cdp 'Runtime.evaluate' @{ expression=$Expression; awaitPromise=$true; returnByValue=$true }
    if ($result.PSObject.Properties['exceptionDetails']) { throw ($result.exceptionDetails | ConvertTo-Json -Depth 12 -Compress) }
    if ($result.result.PSObject.Properties['value']) { return $result.result.value }
}
try {
    $page = $null
    for ($attempt=0; $attempt -lt 30; $attempt++) {
        try {
            $portFile = Join-Path $profileDirectory 'DevToolsActivePort'
            $debugPort = [int](Get-Content -LiteralPath $portFile -ErrorAction Stop | Select-Object -First 1)
            $page = Invoke-RestMethod "http://127.0.0.1:$debugPort/json/new?about:blank" -Method Put -TimeoutSec 2
            break
        }
        catch { Start-Sleep -Milliseconds 200 }
    }
    if ($null -eq $page) { throw 'Isolated Chrome did not start.' }
    $null = $socket.ConnectAsync([Uri]$page.webSocketDebuggerUrl, [Threading.CancellationToken]::None).GetAwaiter().GetResult()
    $null = Invoke-Cdp 'Emulation.setDeviceMetricsOverride' @{width=1280;height=1500;deviceScaleFactor=1;mobile=$false}
    $null = Invoke-Cdp 'Page.navigate' @{url="$BaseUrl/metrics?gameSet=regular_season&preset=custom&startDate=2026-08-25&endDate=2026-08-25#tfs"}
    for ($attempt=0; $attempt -lt 80; $attempt++) {
        if (Invoke-Page "Boolean(document.getElementById('run-metric') && !document.getElementById('run-metric').disabled)") { break }
        Start-Sleep -Milliseconds 100
    }
    $observed = Invoke-Page @'
(async () => {
  const id = x => document.getElementById(x);
  const assert = (value, message) => { if (!value) throw Error(message); };
  assert(id('date-preset').value === 'custom' && id('start-date').value === '2026-08-25', 'Bookmark did not restore dates');
  for (let i=0; i<100 && !id('example-answer').textContent; i++) await new Promise(r=>setTimeout(r,50));
  const buttons = [...document.querySelectorAll('#metric-list button')];
  assert(buttons.length === 20, 'Expected all twenty metric choices');
  for (const button of buttons) {
    button.click();
    assert(id('metric-question').textContent && id('metric-reading').textContent, 'Missing presentation guide: '+button.dataset.id);
    assert(id('metric-technical').textContent.includes(button.dataset.id), 'Technical identity missing');
    assert(id('example-answer').textContent.startsWith('Example result:'), 'Missing worked example: '+button.dataset.id);
    assert(id('example-formula').textContent && id('example-equation').textContent, 'Missing calculation explanation');
    assert(id('result').hidden && id('download-result').disabled, 'Example became a live result');
  }
  buttons.find(b=>b.dataset.id==='tfs').click();
  id('example-choice').value='2'; id('example-choice').dispatchEvent(new Event('change'));
  assert(id('example-answer').textContent.includes('-1/4'), 'Passed-ball example did not update');
  assert(id('result').hidden && id('download-result').disabled, 'Changing example admitted a live score');
  id('run-metric').click();
  for (let i=0; i<600 && id('result').hidden; i++) await new Promise(r=>setTimeout(r,50));
  assert(!id('result').hidden, 'Live metric result did not render: '+id('request-status').textContent);
  assert(id('result').dataset.state === 'partial', 'Award result must be marked partial');
  assert(id('result-dates').textContent.includes('2026-08-25'), 'Response dates are not visible');
  assert(id('award-consequences').textContent.includes('Dylan Beavers'), 'Supported player name did not render');
  assert(id('award-consequences').textContent.includes('25/12'), 'Exact TFS result did not render');
  assert(!id('download-result').disabled, 'Matching result download is disabled');
  id('example-choice').value='1'; id('example-choice').dispatchEvent(new Event('change'));
  assert(id('example-answer').textContent.includes('-5/4'), 'Third-out example did not update');
  assert(id('score-exact').textContent.includes('25/12') && !id('download-result').disabled,
    'Changing illustration altered the actual game result');
  id('metric-detail').scrollIntoView();
  return {badge:id('result-badge').textContent,dates:id('result-dates').textContent,player:'Dylan Beavers',exact:'25/12',workedMetrics:20,examplesIsolatedFromLiveResults:true};
})()
'@
    $dashboard = Invoke-Page @'
(async () => {
  const id=x=>document.getElementById(x), original=window.fetch;
  const assert=(v,m)=>{if(!v)throw Error(m);};
  try {
    let calls=0;
    window.fetch=async(...args)=>{
      const response=await original(...args);
      if(args[0]==='/api/metrics/dashboard'){calls++;window.dashboardCapture=await response.clone().json();}
      return response;
    };
    id('metric-form').requestSubmit();
    for(let i=0;i<600&&id('dashboard-overview').hidden;i++)await new Promise(r=>setTimeout(r,50));
    assert(!id('dashboard-overview').hidden,'Dashboard failed: '+id('dashboard-status').textContent);
    assert(calls===1,'Dashboard issued multiple selection requests');
    const cards=[...document.querySelectorAll('#metric-list button')];
    assert(cards.length===20&&window.dashboardCapture.metrics.length===20,'Dashboard omitted metrics');
    assert(cards.find(b=>b.dataset.id==='tfs').dataset.state==='partial','TFS scope changed');
    assert(cards.find(b=>b.dataset.id==='offensive-reach').querySelector('strong').textContent==='4','Reach integer missing');
    const paq=cards.find(b=>b.dataset.id==='paq-2');
    assert(paq.dataset.state==='unavailable'&&!paq.querySelector('strong').textContent.includes('0'),'Missing PAQ became zero');
    assert(!id('download-dashboard').disabled,'Dashboard download disabled');
    id('metric-group').value='reviews';id('metric-group').dispatchEvent(new Event('change'));
    assert(document.querySelectorAll('#metric-list button').length===2,'Review perspective did not isolate its two metrics');
    assert(!id('download-dashboard').disabled,'Perspective filter invalidated the evidence selection');
    id('metric-group').value='all';id('metric-group').dispatchEvent(new Event('change'));
    id('metric-search').value='Trajectory Fulfillment Score';id('metric-search').dispatchEvent(new Event('input'));
    const aliasCards=[...document.querySelectorAll('#metric-list button')];
    assert(aliasCards.length===1&&aliasCards[0].dataset.id==='tfs','Old name no longer finds the metric');
    aliasCards[0].click();
    assert(id('metric-title').textContent==='Plate Appearance Contribution','New name did not reach detail');
    assert(id('metric-technical').textContent.includes('Trajectory Fulfillment Score'),'Technical alias lost');
    id('metric-search').value='';id('metric-search').dispatchEvent(new Event('input'));
    window.fetch=()=>{throw Error('Card selection must reuse dashboard evidence');};
    cards.find(b=>b.dataset.id==='offensive-reach').click();
    assert(id('score-exact').textContent==='Exact: 4/1','Card detail differs from dashboard');
    id('metric-visibility').value='results';id('metric-visibility').dispatchEvent(new Event('change'));
    assert([...document.querySelectorAll('#metric-list button')].every(b=>['available','partial'].includes(b.dataset.state)),'Result filter included missing scores');
    id('metric-visibility').value='all';id('metric-visibility').dispatchEvent(new Event('change'));
    document.querySelector('[data-id="tfs"]').click();
    document.querySelector('.dashboard').scrollIntoView();
    return {metrics:20,sharedRequests:calls,scopePreserved:true,cardDetailExact:true,
      presentationGuides:20,perspectives:6,legacyNameSearch:true,
      execution:window.dashboardCapture.execution,graphCount:window.dashboardCapture.graphCount};
  } finally {window.fetch=original;}
})()
'@
    $dashboardCapture = Join-Path $profileDirectory 'dashboard-response.json'
    (Invoke-Page 'window.dashboardCapture') | ConvertTo-Json -Depth 60 | Set-Content -LiteralPath $dashboardCapture -Encoding UTF8
    $capture = Invoke-Cdp 'Page.captureScreenshot' @{format='png'}
    [IO.File]::WriteAllBytes($desktopCapture, [Convert]::FromBase64String($capture.data))
    $null = Invoke-Cdp 'Emulation.setDeviceMetricsOverride' @{width=390;height=844;deviceScaleFactor=1;mobile=$true}
    if (-not (Invoke-Page 'document.documentElement.scrollWidth <= innerWidth')) { throw 'Mobile page overflows horizontally.' }
    $null = Invoke-Page "document.querySelector('.dashboard').scrollIntoView()"
    $dashboardMobile = Join-Path $profileDirectory 'dashboard-mobile.png'
    $capture = Invoke-Cdp 'Page.captureScreenshot' @{format='png'}
    [IO.File]::WriteAllBytes($dashboardMobile, [Convert]::FromBase64String($capture.data))
    $null = Invoke-Page "document.getElementById('award-consequences').scrollIntoView()"
    $capture = Invoke-Cdp 'Page.captureScreenshot' @{format='png'}
    [IO.File]::WriteAllBytes($mobileCapture, [Convert]::FromBase64String($capture.data))
    $null = Invoke-Page "document.getElementById('metric-example').open=true; document.getElementById('metric-example').scrollIntoView()"
    if (-not (Invoke-Page 'document.documentElement.scrollWidth <= innerWidth')) { throw 'Mobile example overflows horizontally.' }
    $exampleCapture = Join-Path $profileDirectory 'example-mobile.png'
    $capture = Invoke-Cdp 'Page.captureScreenshot' @{format='png'}
    [IO.File]::WriteAllBytes($exampleCapture, [Convert]::FromBase64String($capture.data))
    $races = Invoke-Page @'
(async () => {
  const id = x => document.getElementById(x), original = window.fetch;
  const assert = (v,m) => { if (!v) throw Error(m); };
  try {
    let resolveOld;
    window.fetch = () => new Promise(resolve => {resolveOld=resolve;});
    id('run-metric').click();
    id('game-set').value='all_star'; id('game-set').dispatchEvent(new Event('change',{bubbles:true}));
    assert(id('result').hidden && id('download-result').disabled, 'Selection change retained old result/download');
    resolveOld(new Response(JSON.stringify({metric:{status:'available',value:{numerator:'999',denominator:'1'}}})));
    await new Promise(r=>setTimeout(r,100));
    assert(id('result').hidden && !id('score-value').textContent.includes('999'), 'Late success overwrote new selection');
    let rejectOld;
    window.fetch = () => new Promise((resolve,reject) => {rejectOld=reject;});
    id('run-metric').click();
    id('start-date').value='2026-08-24'; id('start-date').dispatchEvent(new Event('input',{bubbles:true}));
    rejectOld(Error('obsolete request error'));
    await new Promise(r=>setTimeout(r,100));
    assert(!id('request-status').textContent.includes('obsolete'), 'Late error overwrote current status');
    assert(!id('run-metric').disabled && id('download-result').disabled, 'Selection controls were left stale');
    assert(location.search.includes('2026-08-24') && location.search.includes('all_star'), 'URL selection was not updated');
    let resolveDashboard;
    window.fetch=()=>new Promise(resolve=>{resolveDashboard=resolve;});
    id('metric-form').requestSubmit();
    id('game-set').value='regular_season';id('game-set').dispatchEvent(new Event('change',{bubbles:true}));
    resolveDashboard(new Response(JSON.stringify(window.dashboardCapture)));
    await new Promise(r=>setTimeout(r,100));
    assert(id('dashboard-overview').hidden&&id('download-dashboard').disabled,'Late dashboard response restored stale results');
    assert([...document.querySelectorAll('#metric-list button')].every(b=>b.dataset.state==='unloaded'),'Old dashboard cards retained scores');
    assert(!id('load-dashboard').disabled,'Dashboard refresh remained disabled');
    return {lateSuccessRejected:true,lateErrorRejected:true,lateDashboardRejected:true,staleDownloadDisabled:true,mobileOverflow:false};
  } finally { window.fetch=original; }
})()
'@
    $runProof = $null
    $runCapture = $null
    if ($RunDepthProof) {
        # Render the separately validated real-RDF/SQL proof as an HTTP fixture.
        # This tests presentation and makes no claim of live graph promotion.
        $proofJson = Get-Content -LiteralPath $RunDepthProof -Raw
        $null = Invoke-Page ("window.runDepthProof = " + $proofJson)
        $runProof = Invoke-Page @'
(async () => {
  const id=x=>document.getElementById(x), original=window.fetch;
  const assert=(v,m)=>{if(!v)throw Error(m);};
  try {
    document.querySelector('[data-id="run-construction-depth"]').click();
    const payload=window.runDepthProof;
    payload.dateScope={gameSet:'regular_season',startDate:'2019-04-01',endDate:'2019-04-01'};
    window.fetch=async()=>new Response(JSON.stringify(payload));
    id('run-metric').click();
    for(let i=0;i<100&&id('result').hidden;i++)await new Promise(r=>setTimeout(r,50));
    assert(!id('result').hidden,'Run result failed to render');
    const cards=[...id('run-results').querySelectorAll('article')];
    assert(cards.length===9,'Expected nine complete run histories');
    const flores=cards.find(c=>c.querySelector('h4').textContent==='Player #527038');
    assert(flores?.querySelector('strong').textContent==='3 episodes','Real run depth changed');
    assert(flores.querySelectorAll('li').length===3,'Episode trace is incomplete');
    assert(id('result').dataset.state==='partial'&&id('result-scope').textContent.includes('incomplete'),'Population scope overstated');
    assert(id('coverage').textContent.includes('Observed runs without a result4'),'Missing coverage gap');
    assert(!id('download-result').disabled,'Run evidence download disabled');
    id('run-results').scrollIntoView();
    assert(document.documentElement.scrollWidth<=innerWidth,'Run cards overflow mobile');
    return {fixture:'validated real RDF and SQL, not live promotion',runs:9,unresolvedRuns:4,floresDepth:3,mobileOverflow:false};
  } finally {window.fetch=original;delete window.runDepthProof;}
})()
'@
        $runCapture = Join-Path $profileDirectory 'run-depth-mobile.png'
        $capture = Invoke-Cdp 'Page.captureScreenshot' @{format='png'}
        [IO.File]::WriteAllBytes($runCapture, [Convert]::FromBase64String($capture.data))
    }
    @{live=$observed; dashboard=$dashboard; dashboardCapture=$dashboardCapture; dashboardMobile=$dashboardMobile; regressions=$races; runDepth=$runProof; runCapture=$runCapture; desktopCapture=$desktopCapture; mobileCapture=$mobileCapture; exampleCapture=$exampleCapture} | ConvertTo-Json -Depth 10
} finally {
    if ($socket.State -eq [Net.WebSockets.WebSocketState]::Open) {
        try { $null = Invoke-Cdp 'Browser.close' } catch { }
    }
    $socket.Dispose()
    if (-not $browserProcess.HasExited) { Stop-Process -Id $browserProcess.Id -ErrorAction SilentlyContinue }
}
