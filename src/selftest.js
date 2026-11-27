/** Start-up check: one small READ per company, logged without any secrets. */
import { xeroGet } from './xero.js';
import { COMPANIES, withCompany } from './company.js';

export async function selfTest(config) {
  for (const c of COMPANIES) {
    try {
      await withCompany(c, async () => {
        const org = await xeroGet(config, '/Organisation');
        const o = org?.Organisations?.[0] || {};
        const inv = await xeroGet(config, '/Invoices', { page: 1, order: 'Date DESC' });
        const bt = await xeroGet(config, '/BankTransactions', { page: 1 });
        console.log(`selftest ${c}: OK org="${o.Name}" currency=${o.BaseCurrency} invoices_page1=${(inv.Invoices || []).length} banktx_page1=${(bt.BankTransactions || []).length}`);
      });
    } catch (e) {
      console.log(`selftest ${c}: FAILED ${String(e.message).split('\n')[0]}`);
    }
  }
}
