# LumeOS

Distro Debian 13 (trixie) para jogos e tarefas do dia a dia, com XFCE configurado para lembrar o Windows 11: barra de tarefas inferior com menu iniciar e janelas no centro, relógio e bandeja à direita, tema Fluent, fonte Inter. Gera uma ISO bootável (UEFI e BIOS) com o instalador Calamares. Pensada para um PC com 16 GB de RAM.

## Como gerar a ISO

**Na nuvem (sem Linux):** suba esta pasta para um repositório no GitHub, abra a aba Actions, escolha "Gerar ISO" e clique em Run workflow. Quando terminar, baixe o artefato `lumeos-iso`. Se falhar, baixe o artefato `build-log`.

**Em Debian ou Ubuntu, como root:**

    sudo ./build.sh

A ISO aparece na pasta do projeto, com o log em `build.log`. São necessários uns 15 GB livres e algumas dezenas de minutos. A ISO final deve ter alguns GB, por causa de Wine, Steam e LibreOffice.

**Testar sem pendrive:** abra a ISO em uma máquina virtual (VirtualBox, VMware ou QEMU) com EFI, pelo menos 4 GB de RAM e 25 GB de disco.

## Jogos

- Steam (pacote `steam-installer`, com bibliotecas de 32 bits) e Proton. Se a instalação por apt falhar no build, o primeiro boot instala o Steam por Flatpak.
- Heroic (Epic e GOG) e Bottles por Flatpak, instalados no primeiro boot do sistema já instalado, com internet. O log fica em `journalctl -u lume-firstboot`.
- Lutris, Wine, winetricks, GameMode e MangoHud.
- No Steam, em Propriedades do jogo > Opções de inicialização: `gamemoderun mangohud %command%`. O MangoHud liga e desliga com Shift direito + F12.
- Vulkan e Mesa para AMD e Intel já vêm no sistema. Para NVIDIA, depois de instalar: `sudo lume-gpu-setup`, e reinicie.
- Ajustes de desempenho: `vm.max_map_count` alto (exigido por vários jogos no Proton), escalonador de disco por tipo (NVMe, SSD, HD), zram com zstd limitado a 8 GB, earlyoom, `nowatchdog` no boot, perfil de energia pelo `power-profiles-daemon` e controle de fila de rede BBR.

## Compatibilidade

- Navegadores: Firefox ESR e Chromium. Qualquer outro, por Flatpak (Flathub).
- Programas: Flatpak (Discord, Spotify, OBS e milhares de outros), Wine e Bottles para `.exe`, LibreOffice (Writer, Calc, Impress), VLC.
- Discos e pendrives: NTFS e exFAT, além dos formatos do Linux.
- Controles: suporte do kernel e do Steam Input, Bluetooth com Blueman.

## O que mais está configurado

- XFCE com painel inferior de 44 px: separador expansível, menu Whisker, lista de janelas, separador expansível, bandeja, volume e relógio.
- Tema GTK e ícones Fluent, instalados por `config/hooks/live/0100-theme.hook.chroot`. Se o download falhar, a ISO usa Adwaita.
- Compositor do xfwm4 desligado para menos latência e menos uso de GPU. Para ter sombras e transparência, ative em Ajustes > Ajustes do gerenciador de janelas > Compositor.
- Timers de atualização automática do apt, ModemManager e avahi desativados.

## Limites conhecidos

- Não é Windows. Jogos com anti-cheat de kernel (como Valorant, Fortnite e alguns outros) não rodam no Linux. Confira cada jogo em protondb.com antes de contar com ele.
- Programas do Windows rodam por Wine e Proton, com compatibilidade parcial.
- XFCE não faz cantos arredondados nem a barra de widgets do Windows 11. O visual é uma aproximação.
- O painel está configurado com `p=10`, que deve ser inferior centralizado. Se aparecer em outra borda, ajuste em Painel > Preferências.
- Os nomes exatos de tema e ícones criados pelo Fluent são detectados no build, não fixados.
- Nada disto foi compilado nem iniciado por mim. Os nomes de pacotes, o hook do Steam e o workflow do GitHub são a parte com mais risco de precisar de ajuste na primeira execução.

## Verificar primeiro (em VM)

1. O build termina e gera a ISO. Se falhar, o `build.log` mostra o pacote ou o hook com problema.
2. A ISO inicia em UEFI e em BIOS.
3. O painel aparece embaixo, com menu e janelas centralizados.
4. O log do build mostra "Tema GTK: Fluent-..." e não "Adwaita".
5. `swapon --show` lista `/dev/zram0`; `sysctl vm.max_map_count` mostra 2147483642.
6. `which steam gamemoderun mangohud` encontra os três.
7. Calamares abre e instala em um disco virtual.
8. No sistema instalado, com internet, `flatpak list` mostra Heroic e Bottles depois do primeiro boot.
9. Medir a RAM ociosa com `free -m`.
