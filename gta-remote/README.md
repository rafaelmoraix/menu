# Passa o Controle 🎮

Deixa seus amigos jogarem GTA no seu PC ou Xbox por alguns minutos, direto pelo navegador.
O botão Xbox (o do meio) fica bloqueado.

## Como funciona

```
 Amigo (navegador)                      Seu PC (Windows)                         
 play.html  ── comandos (WebRTC) ──▶  host.html ──▶ agente ──▶ controle virtual ──▶ GTA no PC
            ◀── vídeo + som ─────────  (captura de tela)                         └▶ app Xbox (Jogo Remoto) ──▶ Xbox
```

- **`web/`**: o site. `index.html` é a página inicial, `play.html` é onde o amigo joga, `host.html` é o seu painel.
- **`agent/`**: um programinha Python que roda **só no seu PC**. Ele cria um controle de Xbox virtual e serve o painel em `http://127.0.0.1:8765/host.html`.

O site não "entra" no Xbox sozinho. Seu PC faz a ponte: ele transmite a tela e repassa os comandos para um controle virtual.

## O que você precisa

- PC com **Windows 10/11**, **Chrome ou Edge**, **Python 3.10+** (https://python.org, marque "Add to PATH").
- Para jogar no **Xbox**: o app **Xbox** no PC, com "Recursos remotos" ligados no console (Configurações → Dispositivos e conexões → Recursos remotos).
- Internet razoável de upload (uns 10 Mbps pra ficar bom).

## Passo a passo (você, o dono)

1. Dê dois cliques em **`agent/iniciar.bat`**. Na primeira vez ele instala as dependências e o driver **ViGEmBus** (aceite a instalação). O painel abre sozinho no navegador.
2. Abra o jogo:
   - **GTA no PC:** abra o jogo normalmente.
   - **GTA no Xbox:** no app Xbox do PC, abra seu console → **Jogo remoto**. O jogo vai aparecer numa janela no PC.
3. No painel, confira se está **"agente: ok"**, escolha os minutos por jogador e clique em **Abrir sala**. Escolha a **janela** do GTA (ou do app Xbox) e marque "compartilhar áudio" se aparecer.
4. Mande o **link** pro amigo. Mande o **PIN** separado (outra mensagem, ou de boca).
5. Quando ele aparecer na **Fila**, clique em **Aprovar**.
6. **Deixe a janela do jogo em foco** (clicada) enquanto o amigo joga. Pode deixar o painel aberto em outra janela.

O controle virtual aparece pro jogo como um controle de Xbox comum. Se você também tiver um controle ligado, desligue ele, ou o jogo pode ouvir o seu em vez do virtual.

## Publicar o site (pros amigos abrirem o play.html)

Já publicado em **https://passa-o-controle.netlify.app** (link pros amigos: `/play.html`). O painel já vem com esse endereço.

Para publicar em outro lugar, uma opção é o **GitHub Pages**:

1. No GitHub, abra o repositório → **Settings → Pages**.
2. Em "Branch", escolha a branch que tem a pasta `gta-remote` e a pasta `/ (root)`, e salve.
3. Em alguns minutos o site fica em `https://rafaelmoraix.github.io/menu/gta-remote/web/play.html`.

Se usar outro endereço (Netlify etc.), cole ele no campo **"Endereço público do site"** do painel.

## Segurança

| Proteção | Como |
|---|---|
| Ninguém acha a sala por acaso | Código aleatório de 20 caracteres no link |
| PIN | 6 dígitos. 3 erros = bloqueado. 10 erros somados = PIN troca sozinho |
| Aprovação manual | Ninguém joga sem você clicar em "Aprovar". Um por vez |
| Só controle | O amigo só manda botões e analógicos. Nada de teclado/mouse no seu Windows, nada de arquivos |
| Botão Xbox bloqueado | Descartado em 3 lugares: no navegador do amigo, no seu painel e no agente (que nem tem esse botão no mapa) |
| Agente fechado | Escuta só em `127.0.0.1` e recusa qualquer outro site ou endereço |
| Nada fica preso | Se a conexão cair ou ficar 1s sem comando, o controle virtual solta tudo |
| Tempo + pânico | A vez acaba sozinha. "Tirar jogador" e "Pânico" derrubam na hora |
| Criptografia | Vídeo e comandos vão por WebRTC (criptografado ponta a ponta) |

**Limites que você precisa saber:**

- Os botões **Menu/Start** e **View** funcionam (pausa e mapa do GTA). Só o botão Xbox está bloqueado.
- O amigo controla o GTA como você controlaria. Dentro do jogo, ele pode fazer o que você poderia (gastar dinheiro, entrar em sessão online etc.). Aprove só quem você confia.
- A transmissão captura **a janela que você escolheu**. Escolha a janela do jogo, não a tela inteira, pra não mostrar notificações ou outras coisas.
- A conexão inicial usa o servidor público gratuito do PeerJS. Ele só passa o "aperto de mão"; o vídeo e os comandos não passam por ele.
- Em algumas redes (4G, algumas operadoras) a conexão direta pode não funcionar. Aí seria preciso um servidor TURN.

## Teste rápido sem amigo

Abra o painel, abra a sala e abra o link do amigo numa **janela anônima** no mesmo PC. Entre com o PIN, aprove, e aperte teclas na janela anônima: os botões acendem no painel.
