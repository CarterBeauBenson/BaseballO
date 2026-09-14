[CmdletBinding()]
param(
    [string] $BrowserPath = 'C:\Program Files\Google\Chrome\Application\chrome.exe',
    [string] $BaseUrl = 'http://127.0.0.1:4173'
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
  id('metric-form').requestSubmit();
  for (let i=0; i<600 && id('result').hidden; i++) await new Promise(r=>setTimeout(r,50));
  assert(!id('result').hidden, 'Live metric result did not render: '+id('request-status').textContent);
  assert(id('result').dataset.state === 'partial', 'Award result must be marked partial');
  assert(id('result-dates').textContent.includes('2026-08-25'), 'Response dates are not visible');
  assert(id('award-consequences').textContent.includes('Dylan Beavers'), 'Supported player name did not render');
  assert(id('award-consequences').textContent.includes('25/12'), 'Exact TFS result did not render');
  assert(!id('download-result').disabled, 'Matching result download is disabled');
  id('metric-detail').scrollIntoView();
  return {badge:id('result-badge').textContent,dates:id('result-dates').textContent,player:'Dylan Beavers',exact:'25/12'};
})()
'@
    $capture = Invoke-Cdp 'Page.captureScreenshot' @{format='png'}
    [IO.File]::WriteAllBytes($desktopCapture, [Convert]::FromBase64String($capture.data))
    $null = Invoke-Cdp 'Emulation.setDeviceMetricsOverride' @{width=390;height=844;deviceScaleFactor=1;mobile=$true}
    if (-not (Invoke-Page 'document.documentElement.scrollWidth <= innerWidth')) { throw 'Mobile page overflows horizontally.' }
    $null = Invoke-Page "document.getElementById('award-consequences').scrollIntoView()"
    $capture = Invoke-Cdp 'Page.captureScreenshot' @{format='png'}
    [IO.File]::WriteAllBytes($mobileCapture, [Convert]::FromBase64String($capture.data))
    $races = Invoke-Page @'
(async () => {
  const id = x => document.getElementById(x), original = window.fetch;
  const assert = (v,m) => { if (!v) throw Error(m); };
  try {
    let resolveOld;
    window.fetch = () => new Promise(resolve => {resolveOld=resolve;});
    id('metric-form').requestSubmit();
    id('game-set').value='all_star'; id('game-set').dispatchEvent(new Event('change',{bubbles:true}));
    assert(id('result').hidden && id('download-result').disabled, 'Selection change retained old result/download');
    resolveOld(new Response(JSON.stringify({metric:{status:'available',value:{numerator:'999',denominator:'1'}}})));
    await new Promise(r=>setTimeout(r,100));
    assert(id('result').hidden && !id('score-value').textContent.includes('999'), 'Late success overwrote new selection');
    let rejectOld;
    window.fetch = () => new Promise((resolve,reject) => {rejectOld=reject;});
    id('metric-form').requestSubmit();
    id('start-date').value='2026-08-24'; id('start-date').dispatchEvent(new Event('input',{bubbles:true}));
    rejectOld(Error('obsolete request error'));
    await new Promise(r=>setTimeout(r,100));
    assert(!id('request-status').textContent.includes('obsolete'), 'Late error overwrote current status');
    assert(!id('run-metric').disabled && id('download-result').disabled, 'Selection controls were left stale');
    assert(location.search.includes('2026-08-24') && location.search.includes('all_star'), 'URL selection was not updated');
    return {lateSuccessRejected:true,lateErrorRejected:true,staleDownloadDisabled:true,mobileOverflow:false};
  } finally { window.fetch=original; }
})()
'@
    @{live=$observed; regressions=$races; desktopCapture=$desktopCapture; mobileCapture=$mobileCapture} | ConvertTo-Json -Depth 10
} finally {
    if ($socket.State -eq [Net.WebSockets.WebSocketState]::Open) {
        try { $null = Invoke-Cdp 'Browser.close' } catch { }
    }
    $socket.Dispose()
    if (-not $browserProcess.HasExited) { Stop-Process -Id $browserProcess.Id -ErrorAction SilentlyContinue }
}
