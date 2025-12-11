export const emitApprovalChanged = () => {
  try {
    window.dispatchEvent(new CustomEvent('approval:changed'));
  } catch (e) {
    // no-op
  }
};
