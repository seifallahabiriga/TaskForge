$ErrorActionPreference = "Stop"

$BASE_URL = "http://localhost:8000"

# Generate random user suffix
$randomSuffix = Get-Random -Minimum 1000 -Maximum 9999
$email = "testuser_$randomSuffix@example.com"
$username = "testuser_$randomSuffix"
$password = "StrongPassword123!"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " API DIAGNOSTIC TEST STARTING" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 1. Register User
Write-Host "`n[1] Registering User ($email)..." -ForegroundColor Yellow
$registerBody = @{
    email = $email
    username = $username
    password = $password
} | ConvertTo-Json

try {
    $registerResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Body $registerBody -ContentType "application/json"
    Write-Host "Register Success!" -ForegroundColor Green
    $accessToken = $registerResponse.access_token
} catch {
    Write-Host "Register Failed: $($_.Exception.Message)" -ForegroundColor Red
    exit
}

# 2. Login
Write-Host "`n[2] Logging in to verify credentials..." -ForegroundColor Yellow
$loginBody = @{
    email = $email
    password = $password
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/login" -Method Post -Body $loginBody -ContentType "application/json"
    Write-Host "Login Success!" -ForegroundColor Green
    $accessToken = $loginResponse.access_token
} catch {
    Write-Host "Login Failed: $($_.Exception.Message)" -ForegroundColor Red
    exit
}

# Reusable Header
$headers = @{
    Authorization = "Bearer $accessToken"
    "Content-Type" = "application/json"
}

# 3. Verify Bearer Token (Get My Tasks)
Write-Host "`n[3] Verifying Bearer Token (Fetching /tasks/user/me)..." -ForegroundColor Yellow
try {
    $myTasks = Invoke-RestMethod -Uri "$BASE_URL/tasks/user/me" -Method Get -Headers $headers
    Write-Host "Token verified successfully! Found $($myTasks.Count) existing tasks." -ForegroundColor Green
} catch {
    Write-Host "Token verification failed: $($_.Exception.Message)" -ForegroundColor Red
    exit
}

# 4. Create 3 Tasks
Write-Host "`n[4] Creating 3 Tasks (INFERENCE, ANALYSIS, TRAINING)..." -ForegroundColor Yellow

$taskTypes = @("INFERENCE", "ANALYSIS", "TRAINING")
$createdTasks = @()

foreach ($type in $taskTypes) {
    $taskBody = @{
        name = "Test $type Task"
        task_type = $type
        priority = 1
        input_payload = @{
            prompt = "This is a test prompt for $type"
            data = "Sample data for $type"
        }
    } | ConvertTo-Json -Depth 10

    try {
        $taskRes = Invoke-RestMethod -Uri "$BASE_URL/tasks/" -Method Post -Body $taskBody -Headers $headers
        Write-Host "Created $type Task | ID: $($taskRes.id) | Status: $($taskRes.status)" -ForegroundColor Green
        $createdTasks += $taskRes
    } catch {
        Write-Host "Failed to create $type task: $($_.Exception.Message)" -ForegroundColor Red
        if ($_.ErrorDetails) { Write-Host $_.ErrorDetails.Message -ForegroundColor Red }
    }
}

# 5. Check API Models / Status
Write-Host "`n[5] Fetching explicit status for the first task..." -ForegroundColor Yellow
if ($createdTasks.Count -gt 0) {
    $firstTaskId = $createdTasks[0].id
    try {
        $statusRes = Invoke-RestMethod -Uri "$BASE_URL/tasks/$firstTaskId/status" -Method Get -Headers $headers
        Write-Host "Status Response:" -ForegroundColor Gray
        $statusRes | Format-List | Out-String | Write-Host -ForegroundColor Gray
    } catch {
        Write-Host "Failed to fetch status: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`n=============================================" -ForegroundColor Cyan
Write-Host " API DIAGNOSTIC COMPLETE!" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
