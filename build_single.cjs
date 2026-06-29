// Bundles the whole dashboard into ONE self-contained index.html.
// React, the router, recharts and all pages are compiled and inlined.
// No build step is needed by the end user — just upload the single file.
const esbuild = require("esbuild");
const fs = require("fs");

(async () => {
  const result = await esbuild.build({
    entryPoints: ["src/main.jsx"],
    bundle: true,
    minify: true,
    format: "iife",
    jsx: "automatic",
    loader: { ".js": "jsx", ".css": "empty" },
    define: { "process.env.NODE_ENV": '"production"' },
    write: false,
    logLevel: "info",
  });

  let js = result.outputFiles[0].text;
  // Make it safe to inline inside <script>…</script>
  js = js.split("</script>").join("<\\/script>");

  const css = fs.readFileSync("src/styles.css", "utf8");

  const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Okara Admissions — Superior University</title>
<style>
${css}
</style>
</head>
<body>
<div id="root"></div>
<script>
${js}
</script>
</body>
</html>
`;

  fs.writeFileSync("okara-dashboard.html", html);
  const kb = (Buffer.byteLength(html) / 1024).toFixed(0);
  console.log(`\nWROTE okara-dashboard.html (${kb} KB, single self-contained file)`);
})().catch((e) => { console.error(e); process.exit(1); });
