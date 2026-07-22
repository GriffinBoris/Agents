'use strict';

const path = require('node:path');

function normalizePath(filename) {
  return filename.split(path.sep).join('/');
}

function isAllowed(filename, allowedFiles) {
  const normalizedFilename = normalizePath(filename);
  return allowedFiles.some((allowedFile) => normalizedFilename.endsWith(normalizePath(allowedFile)));
}

module.exports = {
  meta: {
    type: 'problem',
    docs: {
      description: 'Restrict Axios imports to the canonical API client.',
    },
    schema: [
      {
        type: 'object',
        additionalProperties: false,
        properties: {
          allowedFiles: {
            type: 'array',
            items: { type: 'string' },
            minItems: 1,
          },
        },
      },
    ],
    messages: {
      restricted: 'AGVUE001: Axios may only be imported by the canonical API client.',
    },
  },
  create(context) {
    const options = context.options[0] ?? {};
    const allowedFiles = options.allowedFiles ?? ['src/utils/api.ts'];

    return {
      ImportDeclaration(node) {
        const importedModule = node.source.value;
        const importsAxios = importedModule === 'axios' || importedModule.startsWith('axios/');

        if (importsAxios && !isAllowed(context.filename, allowedFiles)) {
          context.report({ node: node.source, messageId: 'restricted' });
        }
      },
    };
  },
};
