// Presentation only. Production callers are removed by the DEV branch.
const developerEvent = 'forge:open-developer-tools';
let open = false;
export function setDeveloperToolsOpen(value: boolean) {
  open = value;
  window.dispatchEvent(new Event(developerEvent));
}
export function openDeveloperTools() {
  setDeveloperToolsOpen(true);
}
export function developerToolsSnapshot() {
  return open;
}
export function subscribeDeveloperTools(listener: () => void) {
  window.addEventListener(developerEvent, listener);
  return () => window.removeEventListener(developerEvent, listener);
}
