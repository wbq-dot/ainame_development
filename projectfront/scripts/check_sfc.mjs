import fs from 'node:fs'
import path from 'node:path'
import vm from 'node:vm'
import { spawnSync } from 'node:child_process'

const projectRoot = path.resolve(import.meta.dirname, '..')
const pagesConfig = JSON.parse(fs.readFileSync(path.join(projectRoot, 'pages.json'), 'utf8'))
const failures = []

function walk(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name)
    return entry.isDirectory() ? walk(target) : [target]
  })
}

function extract(source, tag) {
  const opening = source.match(new RegExp(`<${tag}(?:\\s[^>]*)?>`))
  const closing = source.lastIndexOf(`</${tag}>`)
  if (!opening || closing < 0) return ''
  return source.slice(opening.index + opening[0].length, closing)
}

function checkTemplate(template, file) {
  const stack = []
  const voidTags = new Set(['input', 'image', 'switch'])
  const tagPattern = /<\/?([a-zA-Z][\w-]*)(?:\s[^<>]*?)?\s*\/?>/g
  const normalized = template.replace(/="[^"]*"/g, '=""')
  for (const match of normalized.matchAll(tagPattern)) {
    const raw = match[0]
    const tag = match[1]
    if (raw.startsWith('</')) {
      const expected = stack.pop()
      if (expected !== tag) {
        failures.push(`${file}: 模板标签不匹配，期待 </${expected || '无'}>，实际 </${tag}>`)
        return
      }
    } else if (!raw.endsWith('/>') && !voidTags.has(tag)) {
      stack.push(tag)
    }
  }
  if (stack.length) failures.push(`${file}: 模板缺少 </${stack.at(-1)}>`)
}

function checkScript(script, file) {
  if (typeof vm.SourceTextModule === 'function') {
    new vm.SourceTextModule(script, { identifier: file })
    return
  }
  const result = spawnSync(process.execPath, ['--input-type=module', '--check'], {
    input: script,
    encoding: 'utf8'
  })
  if (result.status !== 0) throw new Error((result.stderr || '语法检查失败').trim())
}

const configuredPaths = new Set()
for (const page of pagesConfig.pages) {
  if (configuredPaths.has(page.path)) failures.push(`pages.json: 重复页面 ${page.path}`)
  configuredPaths.add(page.path)
  const pageFile = path.join(projectRoot, `${page.path}.vue`)
  if (!fs.existsSync(pageFile)) failures.push(`pages.json: 找不到 ${page.path}.vue`)
}

const vueFiles = walk(path.join(projectRoot, 'pages')).filter((file) => file.endsWith('.vue'))
for (const file of vueFiles) {
  const relative = path.relative(projectRoot, file).replaceAll('\\', '/')
  const source = fs.readFileSync(file, 'utf8')
  const template = extract(source, 'template')
  const script = extract(source, 'script')
  if (!template) failures.push(`${relative}: 缺少 template`)
  else checkTemplate(template, relative)
  if (!script) failures.push(`${relative}: 缺少 script`)
  else {
    try {
      checkScript(script, relative)
    } catch (error) {
      failures.push(`${relative}: JavaScript 语法错误：${error.message}`)
    }
  }
}

if (failures.length) {
  console.error(failures.join('\n'))
  process.exit(1)
}

console.log(`检查通过：${vueFiles.length} 个 Vue 页面，${pagesConfig.pages.length} 条页面路由。`)
