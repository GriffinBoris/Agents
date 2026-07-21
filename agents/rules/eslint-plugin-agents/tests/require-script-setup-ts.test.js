'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const rule = require('../rules/require-script-setup-ts');

function runRule(filename, sourceText) {
  const reports = [];
  const context = {
    filename,
    options: [],
    sourceCode: { text: sourceText },
    report(report) {
      reports.push(report);
    },
  };
  const listener = rule.create(context);
  listener.Program({ type: 'Program' });
  return reports;
}

test('accepts script setup and TypeScript in either attribute order', () => {
  assert.deepEqual(runRule('/project/src/App.vue', '<script setup lang="ts"></script>'), []);
  assert.deepEqual(runRule('/project/src/App.vue', "<script lang='ts' setup></script>"), []);
});

test('reports a Vue component without script setup TypeScript', () => {
  const reports = runRule('/project/src/App.vue', '<script lang="ts"></script>');
  assert.equal(reports.length, 1);
  assert.equal(reports[0].messageId, 'required');
});

test('ignores TypeScript modules', () => {
  assert.deepEqual(runRule('/project/src/api.ts', 'export const value = 1;'), []);
});
