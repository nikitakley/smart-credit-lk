// «ООО «Ромашка»» → «Р», «ИП Сидоров А. В.» → «С»
export function initials(name = '') {
  const clean = name.replace(/^(ООО|ОАО|ПАО|АО|ИП)\s+/i, '').replace(/[«»"']/g, '').trim();
  return clean.charAt(0).toUpperCase() || '?';
}

export default function Avatar({ name, light = false }) {
  return <span className={`avatar ${light ? 'avatar--light' : ''}`} aria-hidden="true">{initials(name)}</span>;
}
