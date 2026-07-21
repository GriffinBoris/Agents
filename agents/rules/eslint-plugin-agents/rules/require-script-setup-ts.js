'use strict';

const SCRIPT_SETUP_TYPESCRIPT = /<script\b(?=[^>]*\bsetup\b)(?=[^>]*\blang\s*=\s*(['"])ts\1)[^>]*>/i;

module.exports = {
  meta: {
    type: 'suggestion',
    docs: {
      description: 'Require Vue single-file components to use script setup with TypeScript.',
    },
    schema: [],
    messages: {
      required: 'AGVUE004: new Vue SFCs must use <script setup lang="ts">.',
    },
  },
  create(context) {
    return {
      Program(node) {
        if (!context.filename.endsWith('.vue')) {
          return;
        }

        const sourceText = context.sourceCode.text;
        if (!SCRIPT_SETUP_TYPESCRIPT.test(sourceText)) {
          context.report({ node, messageId: 'required' });
        }
      },
    };
  },
};
