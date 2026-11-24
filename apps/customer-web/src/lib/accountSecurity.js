const UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ";
const LOWER = "abcdefghijkmnopqrstuvwxyz";
const DIGITS = "23456789";
const SYMBOLS = "!@#$%&*?-_";
const ALL = UPPER + LOWER + DIGITS + SYMBOLS;

export function generatePassword(length = 12) {
  const size = Math.max(4, length);
  const random = new Uint32Array(size + 4);
  if (globalThis.crypto?.getRandomValues) globalThis.crypto.getRandomValues(random);
  else for (let i = 0; i < random.length; i += 1) random[i] = Math.floor(Math.random() * 0xffffffff);

  const chars = [
    UPPER[random[0] % UPPER.length],
    LOWER[random[1] % LOWER.length],
    DIGITS[random[2] % DIGITS.length],
    SYMBOLS[random[3] % SYMBOLS.length],
  ];
  for (let i = chars.length; i < size; i += 1) chars.push(ALL[random[i] % ALL.length]);
  for (let i = chars.length - 1; i > 0; i -= 1) {
    const j = random[i + 4] % (i + 1);
    [chars[i], chars[j]] = [chars[j], chars[i]];
  }
  return chars.join("");
}
