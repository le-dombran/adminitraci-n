import http from 'k6/http';
import { check } from 'k6';

const SUPABASE_URL = 'https://vvvjddoiraljjtxqokcc.supabase.co';
const ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ2dmpkZG9pcmFsamp0eHFva2NjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE4OTU3NjYsImV4cCI6MjA5NzQ3MTc2Nn0.GEB41w3qq-tjKd55jZSie2In7JPqv75J6gGgAcrF2Nc';

export const options = {
  stages: [
    { duration: '30s', target: 20 },
    { duration: '1m', target: 50 },
    { duration: '30s', target: 100 },
    { duration: '30s', target: 0 },
  ],
};

export default function () {
  const actions = ['productos', 'ventas', 'usuarios'];
  const action = actions[Math.floor(Math.random() * actions.length)];
  const url = `${SUPABASE_URL}/rest/v1/${action}`;

  // Ajuste según tus columnas reales:
  const payloads = {
    productos: JSON.stringify({ nombre_producto: 'Item_' + __VU, precio: 100, cantidad: 10 }),
    ventas: JSON.stringify({ producto: 'Item_Venta', cantidad: 1, total: 50.0 }),
    usuarios: JSON.stringify({ username: 'User_' + Math.random(), password: 'pwd', nombre_empresa: 'Empresa_' + __VU })
  };

  const params = {
    headers: {
      'apikey': ANON_KEY,
      'Authorization': `Bearer ${ANON_KEY}`,
      'Content-Type': 'application/json',
      'Prefer': 'return=representation',
    },
  };

  const res = http.post(url, payloads[action], params);

  check(res, {
    [`${action} status 201`]: (r) => r.status === 201,
  });
}