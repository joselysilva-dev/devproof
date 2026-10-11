Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap 1200,630
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = 'AntiAlias'
$g.Clear([System.Drawing.ColorTranslator]::FromHtml('#0c1320'))
$white = New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml('#f5f7ff'))
$green = New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml('#a3e635'))
$muted = New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml('#b7c2d5'))
$panel = New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml('#151e2d'))
$g.DrawString('DevProof', ([System.Drawing.Font]::new('Arial',[single]36,[System.Drawing.FontStyle]::Bold)), $white, 70,55)
$g.FillEllipse($green,306,85,18,18)
$g.DrawString('SEU TRABALHO, COM EVIDÊNCIAS', (New-Object System.Drawing.Font 'Arial',16), $green,70,205)
$g.DrawString('Mostre o que você construiu.', ([System.Drawing.Font]::new('Arial',[single]40,[System.Drawing.FontStyle]::Bold)), $white,70,255)
$titles = @('01 / ENTREGA','02 / CONFIRMAÇÃO','03 / VERIFICAÇÃO')
$values = @('Pull request público','Assinatura da carteira','Hash na Solana devnet')
for ($i=0; $i -lt 3; $i++) {
$x=70+370*$i
$g.FillRectangle($panel,$x,370,320,120)
$g.DrawString($titles[$i], (New-Object System.Drawing.Font 'Arial',12), $green,($x+25),390)
$g.DrawString($values[$i], (New-Object System.Drawing.Font 'Arial',18), $white,($x+25),430)
}
$g.DrawString('Protótipo de hackathon · React + FastAPI + SQLite · Somente rede de teste', (New-Object System.Drawing.Font 'Arial',14), $muted,70,540)
$bmp.Save((Join-Path (Get-Location) 'docs/assets/devproof.png'),[System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
