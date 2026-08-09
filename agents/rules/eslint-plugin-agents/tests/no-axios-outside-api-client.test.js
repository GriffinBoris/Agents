'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const rule = require('../rules/no-axios-outside-api-client');

function runRule(filename, importedModule, options = []) {
  const reports = [];
  const context = {
    filename,
    options,
    report(report) {
      reports.push(report);
    },
  };
  const listener = rule.create(context);
  const source = { value: importedModule };
  listener.ImportDeclaration({ source });
  return reports;
}

test('reports Axios outside the canonical API client', () => {
  const reports = runRule('/project/src/views/orders/OrdersView.vue', 'axios');
  assert.equal(reports.length, 1);
  assert.equal(reports[0].messageId, 'restricted');
});

test('allows Axios in a configured canonical API client', () => {
  const reports = runRule('/project/src/core/http.ts', 'axios', [{ allowedFiles: ['src/core/http.ts'] }]);
  assert.deepEqual(reports, []);
});

test('ignores non-Axios imports', () => {
  const reports = runRule('/project/src/views/orders/OrdersView.vue', 'vue');
  assert.deepEqual(reports, []);
});
