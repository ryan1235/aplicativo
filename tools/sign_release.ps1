param(
    [string]$PackageDir = "release\GG Coalition",
    [string]$CertSubject = "CN=GG Coalition Test Code Signing",
    [string]$TimestampServer = "http://timestamp.digicert.com",
    [switch]$NoTimestamp,
    [switch]$Verify
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $PackageDir)) {
    throw "Package directory not found: $PackageDir"
}

$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
    Where-Object { $_.Subject -eq $CertSubject -and $_.HasPrivateKey } |
    Sort-Object NotAfter -Descending |
    Select-Object -First 1

if (-not $cert) {
    throw "Code signing certificate not found in Cert:\CurrentUser\My: $CertSubject"
}

$files = Get-ChildItem -Path $PackageDir -Recurse -Filter *.exe
if (-not $files) {
    throw "No .exe files found under: $PackageDir"
}

foreach ($file in $files) {
    Write-Host "Signing $($file.FullName)"
    if ($NoTimestamp) {
        $result = Set-AuthenticodeSignature -FilePath $file.FullName -Certificate $cert -HashAlgorithm SHA256
    } else {
        try {
            $result = Set-AuthenticodeSignature -FilePath $file.FullName -Certificate $cert -HashAlgorithm SHA256 -TimestampServer $TimestampServer
        } catch {
            Write-Warning "Timestamp failed for $($file.Name), signing without timestamp. $($_.Exception.Message)"
            $result = Set-AuthenticodeSignature -FilePath $file.FullName -Certificate $cert -HashAlgorithm SHA256
        }
    }
    Write-Host "$($file.Name): $($result.Status)"
}

if ($Verify) {
    foreach ($file in $files) {
        $signature = Get-AuthenticodeSignature -FilePath $file.FullName
        Write-Host "$($file.Name): $($signature.Status) - $($signature.SignerCertificate.Subject)"
    }
}
