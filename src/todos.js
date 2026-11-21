const MAX_TITLE = 200;

export function createStore() {
  const items = [];
  let nextId = 1;

  function add(title) {
    if (typeof title !== "string" || title.trim() === "") {
      throw new Error("title is required");
    }
    if (title.length > MAX_TITLE) {
      throw new Error(`title is longer than ${MAX_TITLE} characters`);
    }
    const todo = { id: nextId++, title: title.trim(), done: false };
    items.push(todo);
    return { ...todo };
  }

  function complete(id) {
    const todo = items.find((t) => t.id === id);
    if (!todo) {
      throw new Error(`todo ${id} not found`);
    }
    todo.done = true;
    return { ...todo };
  }

  function list({ done } = {}) {
    return items
      .filter((t) => done === undefined || t.done === done)
      .map((t) => ({ ...t }));
  }

  return { add, complete, list };
}
