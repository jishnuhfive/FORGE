// Synthetic values matching ONLY the names, lengths and validation outcomes in
// the human's sanitized capture. Punctuation is invented, not a live ID format.
export const capturedLaunchFixture = {
  documentId: 'a'.repeat(24),
  workspaceId: 'b'.repeat(24),
  elementId: 'c'.repeat(24),
  companyId: 'cad',
  sessionCompanyId: 'abc',
  server: 'https://cad.onshape.com',
  userId: 'd'.repeat(24),
  clientId: 'synthetic.client:'.padEnd(40, 'x'),
  locale: 'en-US',
  theme: 'abcde',
};
export const capturedLaunchQuery = `?${new URLSearchParams(capturedLaunchFixture)}`;
