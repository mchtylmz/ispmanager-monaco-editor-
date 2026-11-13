export const DEFAULT_PREFERENCES = Object.freeze({
  version: 2, fullscreen: true, theme: 'dark', fontSize: 14, wrap: true, minimap: true, height: 760,
});

export function normalizePreferences(value = {}) {
  return {
    version: 2,
    fullscreen: typeof value?.fullscreen === 'boolean' ? value.fullscreen : DEFAULT_PREFERENCES.fullscreen,
    theme: ['dark', 'light'].includes(value?.theme) ? value.theme : DEFAULT_PREFERENCES.theme,
    fontSize: [12, 14, 16, 18, 20].includes(value?.fontSize) ? value.fontSize : DEFAULT_PREFERENCES.fontSize,
    wrap: typeof value?.wrap === 'boolean' ? value.wrap : DEFAULT_PREFERENCES.wrap,
    minimap: typeof value?.minimap === 'boolean' ? value.minimap : DEFAULT_PREFERENCES.minimap,
    height: [620, 760, 900, 1080].includes(value?.height) ? value.height : DEFAULT_PREFERENCES.height,
  };
}

export function parseConfiguration(hash) {
  if (typeof hash !== 'string' || hash.length > 4096) throw new Error('INVALID_CONFIGURATION');
  const raw = new URLSearchParams(hash.replace(/^#/, '')).get('boot');
  const value = JSON.parse(raw || '{}');
  if (value.version !== 1 || !Array.isArray(value.saveButtons) || !Array.isArray(value.cancelButtons)
      || value.saveButtons.length > 8 || value.cancelButtons.length > 8
      || ![...value.saveButtons, ...value.cancelButtons].every((id) => typeof id === 'string'
        && /^[A-Za-z_][A-Za-z0-9_.-]{0,63}$/.test(id))) throw new Error('INVALID_CONFIGURATION');
  if (value.saveAndCloseButton != null && (value.saveAndCloseButton !== 'ok' || !value.saveButtons.includes('ok'))) {
    throw new Error('INVALID_CONFIGURATION');
  }
  return { preferences: normalizePreferences(value.preferences),
    saveAndCloseButton: value.saveAndCloseButton ?? null,
    saveButtons: [...new Set(value.saveButtons)], cancelButtons: [...new Set(value.cancelButtons)],
    canConfigure: value.canConfigure === true };
}
