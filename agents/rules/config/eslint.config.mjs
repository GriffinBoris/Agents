import eslint from '@eslint/js';
import vue from 'eslint-plugin-vue';
import tseslint from 'typescript-eslint';
import vueParser from 'vue-eslint-parser';

import agents from '../eslint-plugin-agents/index.js';

export default [
  {
    ignores: ['dist/**', 'node_modules/**'],
  },
  eslint.configs.recommended,
  ...tseslint.configs.recommended,
  ...vue.configs['flat/recommended'],
  {
    files: ['frontend/**/*.{ts,vue}', 'src/**/*.{ts,vue}'],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tseslint.parser,
        ecmaVersion: 'latest',
        sourceType: 'module',
      },
    },
    plugins: {
      agents,
    },
    rules: {
      'agents/no-axios-outside-api-client': [
        'error',
        {
          allowedFiles: ['src/utils/api.ts'],
        },
      ],
      'agents/require-script-setup-ts': 'warn',
    },
  },
  {
    files: ['frontend/src/components/**/*.{ts,vue}', 'src/components/**/*.{ts,vue}'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['@/views/**', '@/stores/**', '@/api/**'],
              message: 'AGVUE002: shared components must remain route- and domain-agnostic.',
            },
          ],
        },
      ],
    },
  },
];
