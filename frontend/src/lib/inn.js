// Проверка ИНН по контрольным цифрам (алгоритм ФНС): 10 цифр — юрлицо, 12 — ИП
const checksum = (digits, coeffs) => (coeffs.reduce((sum, c, i) => sum + c * digits[i], 0) % 11) % 10;

export function isValidInn(value) {
  if (!/^(\d{10}|\d{12})$/.test(value)) return false;
  const d = [...value].map(Number);
  if (d.length === 10) return checksum(d, [2, 4, 10, 3, 5, 9, 4, 6, 8]) === d[9];
  return checksum(d, [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) === d[10]
    && checksum(d, [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) === d[11];
}
