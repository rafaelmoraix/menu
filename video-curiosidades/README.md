# video-curiosidades

Geradores das cenas "Vox" (colagem / noir / gibi / planta técnica / palco) do vídeo
"Coisas que usamos todos os dias sem saber que foram criadas por acidente" (canal CROW).
O roteiro e as próximas ideias estão em [`roteiro.md`](roteiro.md).

Cada script em `scripts/` desenha os quadros com Pillow, sintetiza os efeitos sonoros com
NumPy e grava um `.mp4` 1920×1080 a 30 fps com ffmpeg. Não há narração nos vídeos.

## Requisitos
- Python 3 com `pillow` e `numpy`
- `ffmpeg` no PATH
- Fontes (Google Fonts, licença OFL) em `scripts/fonts/`:
  Anton, Abril Fatface, Special Elite, Permanent Marker, Lilita One, Bangers
  ```
  base=https://raw.githubusercontent.com/google/fonts/main
  curl -L -o scripts/fonts/Anton-Regular.ttf $base/ofl/anton/Anton-Regular.ttf
  curl -L -o scripts/fonts/AbrilFatface-Regular.ttf $base/ofl/abrilfatface/AbrilFatface-Regular.ttf
  curl -L -o scripts/fonts/SpecialElite-Regular.ttf $base/apache/specialelite/SpecialElite-Regular.ttf
  curl -L -o scripts/fonts/PermanentMarker-Regular.ttf $base/apache/permanentmarker/PermanentMarker-Regular.ttf
  curl -L -o scripts/fonts/LilitaOne.ttf $base/ofl/lilitaone/LilitaOne-Regular.ttf
  curl -L -o scripts/fonts/Bangers.ttf $base/ofl/bangers/Bangers-Regular.ttf
  ```
- Mapas (só para as cenas com mapa): `npm pack us-atlas@3.0.1` e `npm pack world-atlas@2.0.2`,
  extraídos em `scripts/geo/` (`geo/package/…` e `geo/world/package/…`).

## Imagens de entrada (não versionadas)
- Corvo do canal (fundo vermelho, 736×736) — 1º argumento de todos os scripts.
  Para o encerramento, gere a versão com o corpo estendido:
  `python3 make_crow_ext.py corvo.jpg crow_ext.png`
- Foto do Fahlberg com colher de açúcar (fundo roxo) — 3º argumento dos scripts do #8 em diante.

## Exemplos
```
cd scripts
python3 vox_red_intro.py corvo.jpg vox_vermelho_inicio.mp4
python3 vox_roxo_adocante.py corvo.jpg vox_roxo_adocante.mp4 fahlberg.png
python3 vox_encerramento.py crow_ext.png vox_encerramento.mp4 fahlberg.png
```
Os tempos de cada animação estão nas constantes `T_*` no topo de cada cena; ajuste-os
para casar com a narração gravada.
