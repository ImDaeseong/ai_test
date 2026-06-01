/**
 * Post-build script:
 *  - Copy manifest.json → dist/
 *  - Copy contentScript.js + background.js → dist/
 *  - Copy _locales/ → dist/_locales/
 *  - Create placeholder icons in dist/icons/
 */
import { copyFileSync, mkdirSync, readdirSync, statSync, existsSync, writeFileSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = join(__dirname, '..')
const dist = join(root, 'dist')

function copyDir(src, dest) {
  if (!existsSync(src)) return
  mkdirSync(dest, { recursive: true })
  for (const entry of readdirSync(src)) {
    const srcPath = join(src, entry)
    const destPath = join(dest, entry)
    if (statSync(srcPath).isDirectory()) {
      copyDir(srcPath, destPath)
    } else {
      copyFileSync(srcPath, destPath)
      console.log(`  copied: ${destPath.replace(root, '')}`)
    }
  }
}

// manifest.json
copyFileSync(join(root, 'manifest.json'), join(dist, 'manifest.json'))
console.log('  copied: /dist/manifest.json')

// background.js & contentScript.js (plain JS, no bundling needed)
copyFileSync(join(root, 'src', 'background.js'), join(dist, 'background.js'))
console.log('  copied: /dist/background.js')
copyFileSync(join(root, 'src', 'contentScript.js'), join(dist, 'contentScript.js'))
console.log('  copied: /dist/contentScript.js')

// _locales
copyDir(join(root, '_locales'), join(dist, '_locales'))

// icons (copy from public/icons if present, else create placeholders)
const srcIcons = join(root, 'public', 'icons')
const destIcons = join(dist, 'icons')
mkdirSync(destIcons, { recursive: true })

if (existsSync(srcIcons)) {
  copyDir(srcIcons, destIcons)
} else {
  // Generate minimal 1×1 PNG placeholders so the extension loads without errors
  // (real icons should be replaced before publishing)
  const PLACEHOLDER_PNG = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
    'base64'
  )
  for (const size of [16, 32, 48, 128]) {
    const dest = join(destIcons, `icon${size}.png`)
    writeFileSync(dest, PLACEHOLDER_PNG)
    console.log(`  created placeholder: /dist/icons/icon${size}.png`)
  }
}

console.log('\n✓ Post-build complete. dist/ is ready to load in Chrome.')
