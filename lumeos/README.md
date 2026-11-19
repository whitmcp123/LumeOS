# LumeOS

Distro Debian 13 (trixie) para jogos e tarefas do dia a dia, pensada para um PC com 16 GB de RAM e placa NVIDIA. Mistura o visual de Windows 11 (tema Fluent, janelas limpas), macOS (barra de menu no topo e dock com zoom) e Arch (terminal minimalista com fastfetch). Gera uma ISO bootável (UEFI e BIOS) com o instalador Calamares.

## Como gerar a ISO

**Na nuvem (sem Linux):** suba esta pasta para um repositório no GitHub, abra a aba Actions, escolha "Gerar ISO" e clique em Run workflow. Quando terminar, baixe o artefato `lumeos-iso`. Se falhar, baixe o artefato `build-log`.

**Em Debian ou Ubuntu, como root:**

    sudo ./build.sh

A ISO aparece na pasta do projeto, com o log em `build.log`. São necessários uns 15 GB livres e algumas dezenas de minutos.

**Testar sem pendrive:** abra a ISO em uma máquina virtual (VirtualBox, VMware ou QEMU) com EFI, 4 GB de RAM ou mais e 25 GB de disco. Atenção: em VM não dá para testar o driver NVIDIA, porque a VM não tem a sua placa.

## NVIDIA

- O driver proprietário (`nvidia-driver`, `nvidia-settings`, bibliotecas de 32 bits para o Steam) é instalado dentro da ISO pelo hook `0150-gaming.hook.chroot`, com `nvidia-drm.modeset=1` em `/etc/modprobe.d/lume-nvidia.conf`.
- O módulo de kernel é compilado por DKMS dentro do build. O hook força a compilação para cada kernel instalado e avisa no log se não achar nenhum `nvidia*.ko`. Procure por `AVISO` no `build.log`.
- Pacotes conferidos na documentação do Debian 13: `nvidia-driver`, `nvidia-settings`, `nvidia-smi` (pacote separado) e `nvidia-driver-libs:i386`. A versão padrão do trixie é a série 550. Ela cobre placas GTX e RTX anteriores à série 50; para uma RTX 50 pode ser preciso um driver mais novo.
- Secure Boot: o módulo compilado por DKMS não é assinado, então com Secure Boot ligado ele não carrega. Desligue o Secure Boot na BIOS ou cadastre uma chave (MOK).
- Se o driver não entrar na ISO, no sistema instalado rode `sudo lume-gpu-setup` e reinicie.

## Peso: RAM e SSD

O que foi feito para pesar pouco (nada disto foi medido; confira com `free -m` e `df -h` na VM):

- Fora da ISO: LibreOffice, Chromium, VLC, Wine do sistema e Lutris. Wine e Lutris não vêm porque o Bottles e o Heroic (Flatpak, instalados no primeiro boot) trazem o próprio Wine e o Steam traz o Proton. Para voltar com algum: `sudo apt install libreoffice-writer libreoffice-calc chromium wine`.
- Manuais, documentação e traduções que não sejam pt e en são removidos no último hook (`0900-slim`), e o `dpkg` passa a ignorá-los em instalações futuras.
- Memória: zram com zstd limitado a 8 GB, `zswap` desligado, earlyoom, serviços de segundo plano desativados (timers do apt, ModemManager, avahi), log do sistema limitado a 64 MB, sem arquivos de core dump.
- SSD: `fstrim.timer` ligado e escalonador de disco por tipo (NVMe, SSD, HD).
- Os pacotes "recomendados" do apt continuam ligados. Desligá-los economizaria mais disco, mas eu não consigo validar aqui se a ISO continuaria completa.

## Visual

- Barra no topo estilo menubar do macOS: menu de aplicativos, menu de janelas, bandeja, volume, data e hora.
- Dock (Plank) embaixo, centralizada, com zoom: Iniciar, Firefox, Arquivos, Terminal, Steam e Personalizar. A barra de tarefas inferior do XFCE deixou de existir, a dock faz esse papel.
- O compositor do xfwm4 está **ligado**: é ele que dá transparência para a dock, os widgets e o terminal. Tela cheia dos jogos ignora o compositor (`unredirect_overlays`).
- Tema Fluent e fonte Inter. O terminal usa JetBrains Mono, fundo escuro translúcido e roda `fastfetch` ao abrir (para desligar: `export LUME_NOFETCH=1` no `~/.bashrc`).
- Português do Brasil, teclado `br` e fuso de São Paulo na sessão live. Para outro teclado, edite `--bootappend-live` em `auto/config`.
- Limite: o xfwm4 não tem a animação de minimizar da prévia no navegador. O XFCE também não faz cantos arredondados nem a barra de widgets do Windows 11.

## Widgets de relógio (estilo Rainmeter) e cor do sistema

Abra **Personalizar LumeOS** (menu de aplicativos ou ícone na dock). Ele também abre sozinho no primeiro login.

- Aba Widgets: vários widgets de texto na área de trabalho. Para cada um: texto (hora, dia da semana, data, qualquer combinação de códigos `%H %M %S %A %d %B %Y`), fonte e tamanho (qualquer fonte instalada; para a sua, copie o `.ttf` para `~/.local/share/fonts`), cor, opacidade, sombra, maiúsculas/minúsculas e posição.
- Posição: arraste o widget com o mouse direto na tela (botão direito abre um menu) ou use os controles de posição. "Travar posição" faz os cliques atravessarem o widget.
- Aba Cor do sistema: escolha qualquer cor de destaque (seleções, botões principais, interruptores, barras). A cor é gravada em `~/.config/gtk-3.0/gtk.css` e `~/.config/gtk-4.0/gtk.css`, num bloco marcado que não mexe no resto do arquivo. "Voltar ao padrão do tema" remove o bloco.
- Os dados ficam em `~/.config/lume/widgets.json`. Código: `/usr/local/bin/lume-widgets`, `/usr/local/bin/lume-settings` e `/usr/local/lib/lume/lumecfg.py`.
- A cor de destaque usa regras que sobrepõem o tema. Nos apps GTK3 com o Fluent, o efeito é aproximado (botão principal, seleção, interruptor, barra de progresso). Barras de título e o menu de janelas do xfwm4 não mudam.

## Jogos

- Steam (com bibliotecas de 32 bits) e Proton. Se a instalação por apt falhar no build, o primeiro boot instala o Steam por Flatpak.
- Heroic (Epic e GOG) e Bottles (programas `.exe`) por Flatpak, no primeiro boot do sistema instalado, com internet. Log: `journalctl -u lume-firstboot`.
- GameMode e MangoHud. No Steam, em Propriedades do jogo, Opções de inicialização: `gamemoderun mangohud %command%`. O MangoHud liga e desliga com Shift direito + F12.
- `vm.max_map_count` alto (vários jogos no Proton exigem), BBR, `nowatchdog`.

## Compatibilidade

- Navegador: Firefox ESR. Qualquer outro, por Flatpak (Flathub) ou apt.
- Programas: Flatpak (Discord, Spotify, OBS e milhares de outros), Bottles para `.exe`, mpv para vídeo.
- Discos e pendrives: NTFS e exFAT, além dos formatos do Linux. Controles: kernel, Steam Input e Bluetooth com Blueman.

## Limites conhecidos

- Não é Windows. Jogos com anti-cheat de kernel (Valorant, Fortnite e outros) não rodam no Linux. Confira cada jogo em protondb.com.
- Nada disto foi compilado nem iniciado por mim. O que rodou aqui: `sh -n` nos scripts, `xmllint` nos XMLs, 24 testes da lógica dos widgets (`python3 -m unittest discover -s tests -v`) e uma execução dos dois apps contra um GTK de mentira, que só acha erros de código Python. As janelas GTK reais nunca foram abertas.
- Pontos de maior risco no primeiro build: o driver NVIDIA via DKMS, o hook do Steam, os nomes de tema que o Fluent cria, os padrões da dock (`99_lume-plank.gschema.override`, nomes de chaves do Plank) e a posição do painel (`p=6` deve ser o topo).

## Verificar primeiro (em VM)

1. O build termina. Se falhar, o `build.log` mostra o pacote ou o hook. Procure por `AVISO`.
2. A ISO inicia em UEFI e em BIOS.
3. Barra no topo, dock embaixo e relógio e data soltos na área de trabalho.
4. "Personalizar LumeOS" abre; mudar a fonte e a cor do relógio aparece na hora; arrastar o relógio e reabrir mantém o lugar.
5. A cor do sistema muda em um app GTK (Mousepad, Thunar).
6. `swapon --show` lista `/dev/zram0`; `sysctl vm.max_map_count` mostra 2147483642; `which steam gamemoderun mangohud`.
7. `free -m` e `df -h` depois de instalar, para comparar com o que você espera.
8. No PC real, com a NVIDIA: `nvidia-smi` e `vulkaninfo --summary`.
