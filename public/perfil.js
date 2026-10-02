/* Os três blocos de cada fluxo do catálogo: o que tem, por que usar e o que falta criar para entregar. */
import { el } from './dom.js';

const KIND_LABEL = { cliente: 'cliente fornece', limpar: 'limpar', criar: 'criar', adaptar: 'adaptar' };
const KIND_HINT = {
  cliente: 'Acesso, conta ou chave que o cliente precisa criar e liberar',
  limpar: 'Dado de outra pessoa que veio no arquivo e deve sair antes de usar',
  criar: 'Não existe no fluxo: é trabalho novo',
  adaptar: 'Existe, mas precisa mudar para o negócio do cliente',
};
const EFFORT_LABEL = { baixo: 'adaptação leve', medio: 'adaptação média', alto: 'adaptação pesada' };

function plainList(items) {
  const list = el('ul');
  items.forEach(text => list.append(el('li', '', text)));
  return list;
}

function gapList(gaps) {
  const list = el('ul', 'gaps');
  gaps.forEach(gap => {
    const item = el('li');
    const kind = el('span', `kind ${gap.tipo}`, KIND_LABEL[gap.tipo] ?? gap.tipo);
    kind.title = KIND_HINT[gap.tipo] ?? '';
    item.append(kind, document.createTextNode(` ${gap.texto}`));
    list.append(item);
  });
  return list;
}

function block(className, title, content, badge) {
  const box = el('section', `profile-block ${className}`);
  const head = el('h4', '', title);
  if (badge) head.append(badge);
  box.append(head, content);
  return box;
}

/** Devolve os três blocos, ou null quando o catálogo ainda não tem perfil para o fluxo. */
export function profileBlocks(flow) {
  const profile = flow.profile;
  if (!profile) return null;
  const effort = el('span', `effort ${profile.esforco}`, EFFORT_LABEL[profile.esforco] ?? '');
  effort.title = 'Estimativa a partir da complexidade e da quantidade de trabalho em aberto; não é um orçamento.';
  const wrap = el('div', 'profile');
  wrap.append(
    block('has', 'O que tem', plainList(profile.tem)),
    block('why', 'Por que usar', plainList(profile.por_que)),
    block('missing', 'O que falta criar', profile.falta.length ? gapList(profile.falta) : el('p', 'muted', 'Nada em aberto.'), effort),
  );
  return wrap;
}
