param(
    [string]$CertName = "GG Coalition Test Code Signing",
    [string]$ExportDir = "certs",
    [switch]$TrustForCurrentUser
)

$ErrorActionPreference = "Stop"

$subject = "CN=$CertName"
$exportPath = Join-Path $ExportDir "GG-Coalition-Test-Code-Signing.cer"

New-Item -ItemType Directory -Force -Path $ExportDir | Out-Null

$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
    Where-Object { $_.Subject -eq $subject -and $_.HasPrivateKey } |
    Sort-Object NotAfter -Descending |
    Select-Object -First 1

if (-not $cert) {
    $cert = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject $subject `
        -KeyAlgorithm RSA `
        -KeyLength 3072 `
        -HashAlgorithm SHA256 `
        -KeyUsage DigitalSignature `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -NotAfter (Get-Date).AddYears(3)
}

Export-Certificate -Cert $cert -FilePath $exportPath | Out-Null

if ($TrustForCurrentUser) {
    Import-Certificate -FilePath $exportPath -CertStoreLocation Cert:\CurrentUser\Root | Out-Null
}

Write-Host "Certificate subject: $($cert.Subject)"
Write-Host "Thumbprint: $($cert.Thumbprint)"
Write-Host "Public certificate exported to: $exportPath"
Write-Host "Private key remains in Cert:\CurrentUser\My"

if (-not $TrustForCurrentUser) {
    Write-Host "For local trust, run again with -TrustForCurrentUser or import the .cer into CurrentUser\Root."
}
