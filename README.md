# Redaktor — Azərbaycan dili üçün AI-siz humanizer

Qayda + lüğət əsaslı (süni intellektsiz) Python mühərriki. Brauzerdə Pyodide ilə işləyir (`docs/`), mətn heç yerə göndərilmir.

- `azhum/` — mühərrik (morfologiya, lüğət, cümlə strukturu, məna-qoruma süzgəcləri, proksi metrika)
- `data_src/` — əl ilə yoxlanmış sinonim klasterləri və ifadə qaydaları
- `docs/` — GitHub Pages saytı (`python tools/build_web.py` ilə yenilənir)
- `tests/` — regresiya skriptləri

CLI: `python -m azhum.cli input.txt --level balanced`
