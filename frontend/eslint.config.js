import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import pluginVue from 'eslint-plugin-vue'
import vueParser from 'vue-eslint-parser'

export default [
  // 忽略目录
  { ignores: ['dist/**', 'node_modules/**'] },

  // JS/TS 基础规则
  js.configs.recommended,
  ...tseslint.configs.recommended,

  // Vue 规则（flat config）
  ...pluginVue.configs['flat/recommended'],

  // .vue 文件使用 vue-eslint-parser，TS 部分交给 typescript-eslint
  {
    files: ['**/*.vue'],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tseslint.parser,
        sourceType: 'module',
      },
    },
  },

  // 自定义规则
  {
    rules: {
      'vue/multi-word-component-names': 'off',
    },
  },
]
