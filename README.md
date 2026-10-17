# ¿A qué jugamos?

Web para decidir entre amigos a qué juego de Steam jugar, deslizando cartas al estilo Tinder.

- **Sin cuentas ni servidor propio:** el navegador de quien crea la sala guarda la partida. Los mensajes viajan por un servidor MQTT público y gratuito ([EMQX](https://www.emqx.com/en/mqtt/public-mqtt5-broker)) mediante WebSocket seguro, así que funciona detrás de cualquier router o red móvil. Los mensajes (apodos y votos) no van cifrados de extremo a extremo: no compartáis nada privado.
- **Catálogo de Steam bajo demanda:** la API de Steam no se puede consultar desde el navegador (no permite CORS). Por eso la GitHub Action `.github/workflows/update-catalog.yml` ejecuta `scripts/update_catalog.py`, que regenera `games.json` y vuelve a publicar la web. Solo se lanza a mano, nunca de forma programada:
  - desde la app: el anfitrión pulsa «Actualizar catálogo de Steam» en su sala (se abre GitHub) y la app carga el catálogo nuevo en cuanto está listo, también para los invitados;
  - o en la pestaña **Actions** → «Actualizar catálogo y publicar» → **Run workflow**.
  - Modo `precios` (≈1 min): precios y ofertas. Modo `completo` (≈20 min): también juegos nuevos, reseñas y etiquetas.
  - Solo puede lanzarlo una cuenta con permiso de escritura en el repositorio.

## Cómo se juega

1. Una persona crea la sala y comparte el enlace de «Invitar».
2. Cada uno elige sus temáticas y desliza: → sí, ← no.
3. Cada uno vota todos los juegos por su cuenta: un «no» no se los quita a los demás. Lo que gusta a alguien aparece antes en el mazo del resto.
4. Cuando a todos los conectados les gusta el mismo juego: ¡match!

El anfitrión debe tener la página abierta mientras se vota. Si la recarga, la sala se recupera.
