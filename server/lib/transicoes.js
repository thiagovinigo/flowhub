/* Regras de mudanca de estado de um pedido (ORC-13, ENT-01, ENT-02). Puro: nao le nem grava arquivo. */
export const STATUSES = ['Pedido', 'Discovery', 'Features', 'Orçado', 'Aprovado', 'Em construção', 'Entregue', 'Suporte'];

const filled = (data, key) => Boolean(data[key]);
const missingFields = (data, keys) => keys.filter(key => !filled(data, key));

/** Pre-requisitos de cada estado "travado". As travas valem tambem para quem pula estados. */
const GATES = [
  {
    status: 'Aprovado',
    missing: data => missingFields(data, ['aceite_em', 'aceite_canal', 'versao_proposta', 'aceite_evidencia']),
  },
  {
    status: 'Em construção',
    missing: data => [
      ...(data.entrada_paga === 'true' ? [] : ['entrada_paga (marque a entrada como paga)']),
      ...missingFields(data, ['comprovante']),
    ],
  },
  {
    status: 'Entregue',
    missing: (data, checklist) => {
      const pending = checklist.filter(item => !item.done).length;
      if (checklist.length === 0) return ['checklist de entrega (a seção não existe no pedido)'];
      return pending ? [`checklist de entrega (${pending} de ${checklist.length} itens pendentes)`] : [];
    },
  },
];

export const isBackward = (from, to) => STATUSES.indexOf(to) <= STATUSES.indexOf(from);

/** Lista do que falta para mover de `from` para `to`; vazia quando a mudanca e permitida. */
export function transitionProblems(from, to, data, checklist) {
  if (isBackward(from, to)) return [];
  const targetIndex = STATUSES.indexOf(to);
  return GATES
    .filter(gate => STATUSES.indexOf(gate.status) <= targetIndex)
    .flatMap(gate => gate.missing(data, checklist).map(item => `${item}${gate.status === to ? '' : ` [para ${gate.status}]`}`));
}
