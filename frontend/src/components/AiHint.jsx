// Автоматические подсказки и пояснения системы — только через этот блок (фиолетовый),
// чтобы не путать их с решением банка. Тексты приходят с бэка (systemRecommendation, explanation) или строятся правилами;
// при подключении LLM через бэк сюда придёт ответ модели — ставьте label «Ответ ИИ».
export default function AiHint({ label = 'Подсказка', children }) {
  return (
    <div className="ai-bubble">
      <div className="ai-label">{label}</div>
      <div>{children}</div>
    </div>
  );
}
