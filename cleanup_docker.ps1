$keep_images = @(
    "supabase-mcp-local",
    "ghcr.io/github/github-mcp-server",
    "node"
)

Write-Host "Đang xóa tất cả các container dư thừa..."
$containers = docker ps -aq
if ($containers) {
    docker rm -f $containers
}

Write-Host "Đang dọn dẹp các images không liên quan..."
$images = docker images --format "{{.Repository}} {{.ID}}"
foreach ($line in $images) {
    $parts = $line -split ' '
    $repo = $parts[0]
    $id = $parts[1]

    $should_keep = $false
    foreach ($keep in $keep_images) {
        if ($repo -eq $keep -or $repo -eq "ghcr.io/supabase/mcp-server-supabase") {
            $should_keep = $true
            break
        }
    }
    
    if (-not $should_keep) {
        # Bỏ qua lỗi nếu image đang bị reference chéo
        docker rmi -f $id *>$null
    }
}

docker system prune -f *>$null
Write-Host "Dọn dẹp hoàn tất! Docker hiện tại đã rất gọn gàng."
