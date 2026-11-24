const FALLBACK_NAME = "Kelvin Cahuana";

export function profileNames(user) {
  const fullName = String(user?.name || [user?.nombres, user?.apellidos].filter(Boolean).join(" ") || FALLBACK_NAME).trim() || FALLBACK_NAME;
  const parts = fullName.split(/\s+/).filter(Boolean);
  const splitAt = parts.length >= 4 ? 2 : 1;
  const givenNames = String(user?.nombres || parts.slice(0, splitAt).join(" ")).trim().split(/\s+/).filter(Boolean);
  const surnames = String(user?.apellidos || parts.slice(splitAt).join(" ")).trim().split(/\s+/).filter(Boolean);
  const displayName = [givenNames[0], surnames[0]].filter(Boolean).join(" ") || fullName;

  return {
    fullName,
    displayName,
    initial: displayName.charAt(0).toUpperCase() || "K",
  };
}
