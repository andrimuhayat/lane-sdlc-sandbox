import { test } from "node:test";
import assert from "node:assert/strict";
import { createStore } from "../src/todos.js";

test("add trims the title and starts open", () => {
  const store = createStore();
  assert.deepEqual(store.add("  write tests "), { id: 1, title: "write tests", done: false });
});

test("add rejects an empty or overlong title", () => {
  const store = createStore();
  assert.throws(() => store.add("   "), /title is required/);
  assert.throws(() => store.add("x".repeat(201)), /longer than 200/);
});

test("complete marks one todo done and list filters by state", () => {
  const store = createStore();
  store.add("a");
  store.add("b");
  store.complete(2);
  assert.deepEqual(store.list({ done: true }).map((t) => t.id), [2]);
  assert.deepEqual(store.list({ done: false }).map((t) => t.id), [1]);
  assert.equal(store.list().length, 2);
});

test("complete fails for an unknown id", () => {
  const store = createStore();
  assert.throws(() => store.complete(9), /todo 9 not found/);
});
