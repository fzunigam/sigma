'use client';

import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  ArrowLeftRight,
  Plus,
  RefreshCw,
  Trash2,
  CreditCard,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Sun,
  Moon,
  Info,
  X
} from 'lucide-react';

const API_URL = '';

interface Account {
  id: string;
  name: string;
  type: 'debit' | 'credit';
  balance: number;
  credit_limit: number;
}

interface Transaction {
  unique_id: string;
  type: string;
  amount: number;
  description: string;
  account_id: string;
  created_at: string;
}

interface RenderSnapshot {
  id: string;
  net_amount: number;
  rendered_at: string;
}

interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info';
  text: string;
}

export default function Dashboard() {
  // Theme Toggler
  const [isDark, setIsDark] = useState(true);

  // Navigation Tab
  const [activeTab, setActiveTab] = useState<'dashboard' | 'accounts' | 'history'>('dashboard');

  // Core Data States
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [renderHistory, setRenderHistory] = useState<RenderSnapshot[]>([]);
  const [markedTotal, setMarkedTotal] = useState<number>(0);
  const [netBalance, setNetBalance] = useState<number>(0);
  const [defaults, setDefaults] = useState({ income_acc: '', expense_acc: '' });

  // UI Loaders and Actions States
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  // Modals States
  const [showRenderModal, setShowRenderModal] = useState(false);
  const [showNewAccountModal, setShowNewAccountModal] = useState(false);
  const [showRenameModal, setShowRenameModal] = useState<Account | null>(null);
  const [showLimitModal, setShowLimitModal] = useState<Account | null>(null);

  // Form Fields State
  const [txType, setTxType] = useState<'expense' | 'income' | 'transfer'>('expense');
  const [txAmount, setTxAmount] = useState('');
  const [txDesc, setTxDesc] = useState('');
  const [txAccount, setTxAccount] = useState('');
  const [txTransferTo, setTxTransferTo] = useState('');
  const [txDate, setTxDate] = useState('');
  const [txMark, setTxMark] = useState(true);
  const [txError, setTxError] = useState('');

  // New Account Fields
  const [newAccId, setNewAccId] = useState('');
  const [newAccName, setNewAccName] = useState('');
  const [newAccType, setNewAccType] = useState<'debit' | 'credit'>('debit');
  const [newAccBalance, setNewAccBalance] = useState('');
  const [newAccLimit, setNewAccLimit] = useState('');
  const [newAccError, setNewAccError] = useState('');

  // Modals Input States
  const [renameValue, setRenameValue] = useState('');
  const [limitValue, setLimitValue] = useState('');

  // Table confirmation ID
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Toggle Dark Mode Class
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  // Load Status and Configuration
  const fetchData = async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    try {
      const resStatus = await fetch(`${API_URL}/api/v1/status`);
      if (!resStatus.ok) throw new Error('Failed to load database status.');
      const dataStatus = await resStatus.json();
      setAccounts(dataStatus.accounts || []);
      setMarkedTotal(dataStatus.marked_total || 0);
      setNetBalance(dataStatus.net_balance || 0);

      const resConfig = await fetch(`${API_URL}/api/v1/config`);
      if (resConfig.ok) {
        const dataConfig = await resConfig.json();
        setDefaults(dataConfig);
        if (txType === 'expense' && dataConfig.expense_acc) {
          setTxAccount(dataConfig.expense_acc);
        } else if (txType === 'income' && dataConfig.income_acc) {
          setTxAccount(dataConfig.income_acc);
        } else if (dataStatus.accounts?.length > 0) {
          setTxAccount(dataStatus.accounts[0].id);
        }
      }

      const resTx = await fetch(`${API_URL}/api/v1/transactions?limit=30`);
      if (resTx.ok) {
        setTransactions(await resTx.json());
      }

      const resHist = await fetch(`${API_URL}/api/v1/render/history?limit=20`);
      if (resHist.ok) {
        setRenderHistory(await resHist.json());
      }
    } catch (error: any) {
      addToast('error', error.message || 'Error communicating with local server.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (txType === 'expense' && defaults.expense_acc) {
      setTxAccount(defaults.expense_acc);
    } else if (txType === 'income' && defaults.income_acc) {
      setTxAccount(defaults.income_acc);
    } else if (accounts.length > 0) {
      setTxAccount(accounts[0].id);
    }
  }, [txType, defaults, accounts]);

  const addToast = (type: 'success' | 'error' | 'info', text: string) => {
    const id = Math.random().toString(36).substr(2, 9);
    setToasts((prev) => [...prev, { id, type, text }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  const formatCLP = (amount: number) => {
    const isNegative = amount < 0;
    const absAmount = Math.abs(amount);
    const formatted = new Intl.NumberFormat('es-CL').format(absAmount);
    return `${isNegative ? '-\xa0' : ''}$${formatted}`;
  };

  const handleLogTransaction = async (e: React.FormEvent) => {
    e.preventDefault();
    setTxError('');

    const amountNum = parseInt(txAmount, 10);
    if (isNaN(amountNum) || amountNum <= 0) {
      setTxError('Amount must be a positive integer.');
      return;
    }

    if (!txDesc.trim()) {
      setTxError('Description is required.');
      return;
    }

    setIsSubmitting(true);
    try {
      let endpoint = '';
      let payload: any = {};

      if (txType === 'expense') {
        endpoint = '/api/v1/transactions/expense';
        payload = {
          amount: amountNum,
          description: txDesc.trim(),
          mark: txMark,
          account_id: txAccount || null,
          date: txDate || null,
        };
      } else if (txType === 'income') {
        endpoint = '/api/v1/transactions/income';
        payload = {
          amount: amountNum,
          description: txDesc.trim(),
          mark: txMark,
          account_id: txAccount || null,
          date: txDate || null,
        };
      } else {
        if (!txAccount || !txTransferTo) {
          setTxError('Both source and destination accounts are required.');
          setIsSubmitting(false);
          return;
        }
        if (txAccount === txTransferTo) {
          setTxError('Source and destination accounts must be identical.');
          setIsSubmitting(false);
          return;
        }
        endpoint = '/api/v1/transactions/transfer';
        payload = {
          from_account: txAccount,
          to_account: txTransferTo,
          amount: amountNum,
          date: txDate || null,
        };
      }

      const res = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to record transaction.');

      addToast('success', `Transaction logged: ${data.id}`);
      setTxAmount('');
      setTxDesc('');
      setTxDate('');
      fetchData(false);
    } catch (err: any) {
      setTxError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteTransaction = async (uniqueId: string) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/transactions/${uniqueId}`, {
        method: 'DELETE',
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Deletion failed.');
      }
      addToast('success', 'Transaction deleted.');
      setDeleteConfirmId(null);
      fetchData(false);
    } catch (err: any) {
      addToast('error', err.message);
    }
  };

  const handleExecuteRender = async () => {
    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/render`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Render process failed.');
      addToast('success', `Render executed: ${formatCLP(data.net_amount)}`);
      setShowRenderModal(false);
      fetchData(false);
    } catch (err: any) {
      addToast('error', err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    setNewAccError('');

    if (!newAccId.trim() || !newAccName.trim()) {
      setNewAccError('Account ID and Display Name are required.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/accounts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: newAccId.trim(),
          name: newAccName.trim(),
          type: newAccType,
          initial_balance: parseInt(newAccBalance, 10) || 0,
          credit_limit: parseInt(newAccLimit, 10) || 0,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Account creation failed.');

      addToast('success', `Account '${data.account.id}' created.`);
      setShowNewAccountModal(false);
      setNewAccId('');
      setNewAccName('');
      setNewAccBalance('');
      setNewAccLimit('');
      fetchData(false);
    } catch (err: any) {
      setNewAccError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRenameAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!showRenameModal) return;

    try {
      const res = await fetch(`${API_URL}/api/v1/accounts/${showRenameModal.id}/rename`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_id: renameValue.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Rename request failed.');
      addToast('success', `Renamed account to '${data.account.id}'`);
      setShowRenameModal(null);
      setRenameValue('');
      fetchData(false);
    } catch (err: any) {
      addToast('error', err.message);
    }
  };

  const handleUpdateLimit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!showLimitModal) return;

    try {
      const res = await fetch(`${API_URL}/api/v1/accounts/${showLimitModal.id}/limit`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: parseInt(limitValue, 10) || 0 }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Limit update failed.');
      addToast('success', `Limit updated for '${data.account.id}'`);
      setShowLimitModal(null);
      setLimitValue('');
      fetchData(false);
    } catch (err: any) {
      addToast('error', err.message);
    }
  };

  const handleDeleteAccount = async (id: string) => {
    if (!confirm(`Confirm deletion of account '${id}'? Transactions are retained under 'deleted'.`)) return;

    try {
      const res = await fetch(`${API_URL}/api/v1/accounts/${id}`, { method: 'DELETE' });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Deletion failed.');
      }
      addToast('success', `Account deleted: ${id}`);
      fetchData(false);
    } catch (err: any) {
      addToast('error', err.message);
    }
  };

  return (
    <div className="flex min-h-screen bg-background text-foreground font-sans">

      {/* 1. Minimal Sidebar */}
      <aside className="w-64 bg-card border-r border-border p-6 flex flex-col justify-between">
        <div>
          <div className="flex items-center gap-3 mb-8">
            <div className="w-8 h-8 rounded-md bg-primary text-primary-foreground flex items-center justify-center font-mono font-bold text-lg">
              Σ
            </div>
            <div>
              <h1 className="font-bold text-base tracking-tight leading-tight">Sigma</h1>
              <span className="text-xs text-muted-foreground">Finance Tracker</span>
            </div>
          </div>

          <nav className="flex flex-col gap-1">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`flex items-center gap-3 w-full px-3 py-2 text-sm rounded-md transition-colors ${activeTab === 'dashboard'
                ? 'bg-secondary text-secondary-foreground font-medium border border-border'
                : 'text-muted-foreground hover:bg-secondary/40 hover:text-foreground'
                }`}
            >
              <TrendingUp size={16} />
              <span>Dashboard</span>
            </button>
            <button
              onClick={() => setActiveTab('accounts')}
              className={`flex items-center gap-3 w-full px-3 py-2 text-sm rounded-md transition-colors ${activeTab === 'accounts'
                ? 'bg-secondary text-secondary-foreground font-medium border border-border'
                : 'text-muted-foreground hover:bg-secondary/40 hover:text-foreground'
                }`}
            >
              <CreditCard size={16} />
              <span>Accounts</span>
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`flex items-center gap-3 w-full px-3 py-2 text-sm rounded-md transition-colors ${activeTab === 'history'
                ? 'bg-secondary text-secondary-foreground font-medium border border-border'
                : 'text-muted-foreground hover:bg-secondary/40 hover:text-foreground'
                }`}
            >
              <FileText size={16} />
              <span>Render History</span>
            </button>
          </nav>
        </div>

        <div>
          {/* Theme Selector / Status */}
          <div className="flex items-center justify-between border-t border-border pt-4 text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isLoading ? 'bg-unbalanced animate-pulse' : 'bg-balanced'}`}></div>
              <span>{isLoading ? 'Syncing…' : 'Sync Active'}</span>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setIsDark(!isDark)}
                aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
                className="hover:text-foreground p-1 transition-colors"
              >
                {isDark ? <Sun size={14} /> : <Moon size={14} />}
              </button>
              <button
                onClick={() => fetchData(true)}
                aria-label="Refresh data"
                className="hover:text-foreground p-1 transition-colors"
              >
                <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* 2. Main Dashboard Content */}
      <main className="flex-1 p-8 overflow-y-auto h-screen animate-in fade-in duration-200">

        {/* --- TAB: DASHBOARD --- */}
        {activeTab === 'dashboard' && (
          <div className="space-y-8">

            {/* Minimalist Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

              {/* Card 1: Net Balance */}
              <div className="bg-card border border-border rounded-lg p-6 flex flex-col justify-between">
                <div>
                  <span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Net Balance</span>
                  <h2 className="text-3xl font-bold mt-2 tabular-nums">
                    {formatCLP(netBalance)}
                  </h2>
                </div>
                <span className="text-[10px] text-muted-foreground mt-4 block">Calculated liquid asset net worth</span>
              </div>

              {/* Card 2: Pending Render */}
              <div className="bg-card border border-border rounded-lg p-6 flex flex-col justify-between">
                <div>
                  <span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Pending Marked Sum</span>
                  <h2 className={`text-3xl font-bold mt-2 tabular-nums ${markedTotal > 0 ? 'text-balanced' : markedTotal < 0 ? 'text-unbalanced' : ''}`}>
                    {formatCLP(markedTotal)}
                  </h2>
                </div>
                <span className="text-[10px] text-muted-foreground mt-4 block">Sum of active transaction cycle</span>
              </div>

              {/* Card 3: Quick Action Render */}
              <div className="bg-card border border-border rounded-lg p-6 flex flex-col justify-between">
                <div>
                  <span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Verification Node</span>
                  <p className="text-xs text-muted-foreground mt-2">Close the active audit cycle and commit marked items to render history.</p>
                </div>
                <button
                  onClick={() => setShowRenderModal(true)}
                  disabled={markedTotal === 0 || isSubmitting}
                  className="w-full bg-primary text-primary-foreground font-medium py-2 rounded-md text-sm mt-4 hover:opacity-90 disabled:opacity-30 disabled:cursor-not-allowed transition-opacity flex justify-center items-center gap-2"
                >
                  {isSubmitting ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                  <span>Render Cycle</span>
                </button>
              </div>

            </div>

            {/* Split Panel Layout */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8 items-start">

              {/* Left Panel: Accounts & Logs */}
              <div className="xl:col-span-2 space-y-8">

                {/* Minimalist Accounts Grid */}
                <div>
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-base font-semibold">Accounts</h3>
                    <button
                      onClick={() => setShowNewAccountModal(true)}
                      className="text-xs text-muted-foreground hover:text-foreground font-medium transition-colors flex items-center gap-1"
                    >
                      <Plus size={14} />
                      Add Account
                    </button>
                  </div>

                  {accounts.length === 0 ? (
                    <div className="bg-card border border-border border-dashed rounded-lg p-8 text-center text-sm text-muted-foreground">
                      No accounts found. Use "Add Account" to configure.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {accounts.map((acc) => (
                        <div key={acc.id} className="bg-card border border-border rounded-lg p-4 flex flex-col justify-between min-h-28">
                          <div className="flex justify-between items-start">
                            <div>
                              <h4 className="font-semibold text-sm">{acc.name}</h4>
                              <span className="text-[10px] text-muted-foreground font-mono uppercase">{acc.id}</span>
                            </div>
                            <span className="text-[10px] px-2 py-0.5 border border-border rounded font-mono uppercase text-muted-foreground bg-muted/30">
                              {acc.type}
                            </span>
                          </div>

                          <div className="mt-4 flex justify-between items-baseline">
                            <span className="text-[10px] text-muted-foreground">Balance</span>
                            <span className="text-base font-bold tabular-nums">{formatCLP(acc.balance)}</span>
                          </div>

                          {acc.type === 'credit' && acc.credit_limit > 0 && (
                            <div className="mt-2 space-y-1">
                              <div className="flex justify-between text-[8px] text-muted-foreground">
                                <span>Util: {Math.round((acc.balance / acc.credit_limit) * 100)}%</span>
                                <span>Limit: {formatCLP(acc.credit_limit)}</span>
                              </div>
                              <div className="h-1 bg-secondary rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-unbalanced"
                                  style={{ width: `${Math.min((acc.balance / acc.credit_limit) * 100, 100)}%` }}
                                ></div>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Minimalist Transactions Table */}
                <div>
                  <h3 className="text-base font-semibold mb-4">Chronological Activity</h3>
                  <div className="bg-card border border-border rounded-lg overflow-hidden">
                    {transactions.length === 0 ? (
                      <div className="p-8 text-center text-sm text-muted-foreground">
                        No transactions registered yet.
                      </div>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm border-collapse">
                          <thead>
                            <tr className="border-b border-border text-muted-foreground text-[10px] uppercase font-semibold">
                              <th className="p-3">Type</th>
                              <th className="p-3">Description</th>
                              <th className="p-3">Account</th>
                              <th className="p-3 text-right">Amount</th>
                              <th className="p-3">Date</th>
                              <th className="p-3 text-center w-24">Action</th>
                            </tr>
                          </thead>
                          <tbody>
                            {transactions.map((tx) => (
                              <tr key={tx.unique_id} className="border-b border-border hover:bg-secondary/20 transition-colors">
                                <td className="p-3 font-mono text-xs">
                                  <span className="flex items-center gap-2">
                                    {tx.type === 'income' ? (
                                      <TrendingUp size={12} className="text-balanced" />
                                    ) : tx.type === 'expense' ? (
                                      <TrendingDown size={12} className="text-unbalanced" />
                                    ) : (
                                      <ArrowLeftRight size={12} className="text-muted-foreground" />
                                    )}
                                    <span className="capitalize">{tx.type}</span>
                                  </span>
                                </td>
                                <td className="p-3 font-medium text-foreground">{tx.description}</td>
                                <td className="p-3 text-muted-foreground text-xs font-mono">{tx.account_id || '—'}</td>
                                <td className={`p-3 text-right font-bold tabular-nums ${tx.type === 'income' ? 'text-balanced' : tx.type === 'expense' ? 'text-unbalanced' : ''}`}>
                                  {tx.type === 'expense' ? '-' : ''}{formatCLP(tx.amount)}
                                </td>
                                <td className="p-3 text-muted-foreground text-xs font-mono">{tx.created_at.substring(0, 10)}</td>
                                <td className="p-3 text-center">
                                  {deleteConfirmId === tx.unique_id ? (
                                    <div className="flex gap-1 justify-center">
                                      <button
                                        onClick={() => handleDeleteTransaction(tx.unique_id)}
                                        className="bg-destructive text-primary-foreground text-[10px] font-semibold px-2 py-0.5 rounded hover:opacity-90"
                                      >
                                        Delete
                                      </button>
                                      <button
                                        onClick={() => setDeleteConfirmId(null)}
                                        className="bg-secondary text-secondary-foreground text-[10px] px-2 py-0.5 rounded border border-border"
                                      >
                                        No
                                      </button>
                                    </div>
                                  ) : (
                                    <button
                                      onClick={() => setDeleteConfirmId(tx.unique_id)}
                                      aria-label={`Delete record ${tx.unique_id}`}
                                      className="text-muted-foreground hover:text-destructive p-1 transition-colors"
                                    >
                                      <Trash2 size={14} />
                                    </button>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </div>

              </div>

              {/* Right Panel: Tabbed Form Logger */}
              <div className="bg-card border border-border rounded-lg p-6 space-y-4">
                <h3 className="text-base font-semibold">Quick Logger</h3>

                {/* Flat selection tabs */}
                <div className="flex border-b border-border text-sm">
                  {(['expense', 'income', 'transfer'] as const).map((type) => (
                    <button
                      key={type}
                      onClick={() => setTxType(type)}
                      className={`flex-1 pb-2 font-medium capitalize text-center ${txType === type
                        ? 'border-b-2 border-primary text-foreground'
                        : 'text-muted-foreground hover:text-foreground'
                        }`}
                    >
                      {type}
                    </button>
                  ))}
                </div>

                <form onSubmit={handleLogTransaction} className="space-y-4 text-sm">
                  <div>
                    <label htmlFor="tx-amount" className="block text-xs text-muted-foreground mb-1">Amount (CLP)</label>
                    <input
                      id="tx-amount"
                      type="number"
                      inputMode="numeric"
                      value={txAmount}
                      onChange={(e) => setTxAmount(e.target.value)}
                      placeholder="e.g. 5000"
                      required
                      className="bg-background border border-border text-foreground rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring w-full"
                    />
                  </div>

                  <div>
                    <label htmlFor="tx-desc" className="block text-xs text-muted-foreground mb-1">Description</label>
                    <input
                      id="tx-desc"
                      type="text"
                      value={txDesc}
                      onChange={(e) => setTxDesc(e.target.value)}
                      placeholder="e.g. Groceries, Utility, Paycheck"
                      required
                      className="bg-background border border-border text-foreground rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring w-full"
                    />
                  </div>

                  <div>
                    <label htmlFor="tx-account" className="block text-xs text-muted-foreground mb-1">
                      {txType === 'transfer' ? 'From Account' : 'Account'}
                    </label>
                    <select
                      id="tx-account"
                      value={txAccount}
                      onChange={(e) => setTxAccount(e.target.value)}
                      className="bg-background border border-border text-foreground rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring w-full"
                    >
                      {accounts.map((acc) => (
                        <option key={acc.id} value={acc.id}>{acc.name} ({acc.id})</option>
                      ))}
                    </select>
                  </div>

                  {txType === 'transfer' && (
                    <div>
                      <label htmlFor="tx-transfer-to" className="block text-xs text-muted-foreground mb-1">To Account</label>
                      <select
                        id="tx-transfer-to"
                        value={txTransferTo}
                        onChange={(e) => setTxTransferTo(e.target.value)}
                        className="bg-background border border-border text-foreground rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring w-full"
                      >
                        <option value="">-- Choose Account --</option>
                        {accounts.map((acc) => (
                          <option key={acc.id} value={acc.id}>{acc.name} ({acc.id})</option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div>
                    <label htmlFor="tx-date" className="block text-xs text-muted-foreground mb-1">Date Override (Optional)</label>
                    <input
                      id="tx-date"
                      type="date"
                      value={txDate}
                      onChange={(e) => setTxDate(e.target.value)}
                      className="bg-background border border-border text-foreground rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring w-full"
                    />
                  </div>

                  {txType !== 'transfer' && (
                    <div className="flex items-center gap-2 py-1">
                      <input
                        id="tx-mark"
                        type="checkbox"
                        checked={txMark}
                        onChange={(e) => setTxMark(e.target.checked)}
                        className="w-4 h-4 rounded border-border text-primary focus:ring-ring"
                      />
                      <label htmlFor="tx-mark" className="text-xs text-muted-foreground cursor-pointer select-none">Mark for render cycle</label>
                    </div>
                  )}

                  {txError && (
                    <div className="flex items-center gap-2 p-3 bg-destructive/10 border border-destructive text-destructive rounded-md text-xs">
                      <AlertCircle size={14} className="shrink-0" />
                      <span>{txError}</span>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isSubmitting || accounts.length === 0}
                    className="w-full bg-primary text-primary-foreground font-semibold py-2 rounded-md hover:opacity-90 disabled:opacity-30 disabled:cursor-not-allowed transition-opacity flex justify-center items-center gap-2"
                  >
                    {isSubmitting && <Loader2 size={14} className="animate-spin" />}
                    <span>{isSubmitting ? 'Submitting…' : 'Log Transaction'}</span>
                  </button>
                </form>
              </div>

            </div>

          </div>
        )}

        {/* --- TAB: ACCOUNTS CONFIGURATION --- */}
        {activeTab === 'accounts' && (
          <div className="space-y-8">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-xl font-bold tracking-tight">Accounts Management</h2>
                <p className="text-xs text-muted-foreground mt-1">Configure ledgers, debt limits, and default tracking paths.</p>
              </div>
              <button
                onClick={() => setShowNewAccountModal(true)}
                className="bg-primary text-primary-foreground font-semibold px-4 py-2 rounded-md text-sm hover:opacity-90 transition-opacity flex items-center gap-2"
              >
                <Plus size={16} />
                Create Account
              </button>
            </div>

            <div className="bg-card border border-border rounded-lg overflow-hidden">
              {accounts.length === 0 ? (
                <div className="p-8 text-center text-sm text-muted-foreground">
                  No accounts found. Use "Create Account" to add your first.
                </div>
              ) : (
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-border text-muted-foreground text-[10px] uppercase font-semibold">
                      <th className="p-4">Short ID</th>
                      <th className="p-4">Name</th>
                      <th className="p-4">Type</th>
                      <th className="p-4 text-right">Balance</th>
                      <th className="p-4 text-right">Credit Limit</th>
                      <th className="p-4 text-center w-56">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {accounts.map((acc) => (
                      <tr key={acc.id} className="border-b border-border hover:bg-secondary/20 transition-colors">
                        <td className="p-4 font-mono font-bold text-xs">{acc.id}</td>
                        <td className="p-4 font-medium">{acc.name}</td>
                        <td className="p-4">
                          <span className="text-[10px] px-2 py-0.5 border border-border rounded font-mono uppercase text-muted-foreground bg-muted/30">
                            {acc.type}
                          </span>
                        </td>
                        <td className="p-4 text-right font-bold tabular-nums">{formatCLP(acc.balance)}</td>
                        <td className="p-4 text-right text-muted-foreground tabular-nums">
                          {acc.type === 'credit' ? formatCLP(acc.credit_limit) : '—'}
                        </td>
                        <td className="p-4 text-center">
                          <div className="flex gap-2 justify-center">
                            <button
                              onClick={() => {
                                setRenameValue(acc.id);
                                setShowRenameModal(acc);
                              }}
                              className="bg-secondary text-secondary-foreground border border-border hover:bg-muted text-xs px-2.5 py-1 rounded"
                            >
                              Rename
                            </button>
                            {acc.type === 'credit' && (
                              <button
                                onClick={() => {
                                  setLimitValue(acc.credit_limit.toString());
                                  setShowLimitModal(acc);
                                }}
                                className="bg-secondary text-secondary-foreground border border-border hover:bg-muted text-xs px-2.5 py-1 rounded"
                              >
                                Limit
                              </button>
                            )}
                            <button
                              onClick={() => handleDeleteAccount(acc.id)}
                              className="border border-destructive/20 text-destructive bg-destructive/5 hover:bg-destructive/10 text-xs px-2.5 py-1 rounded"
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* Config Panel */}
            <div className="bg-card border border-border rounded-lg p-6 space-y-4">
              <div>
                <h3 className="text-base font-semibold">Smart Defaults</h3>
                <p className="text-xs text-muted-foreground mt-0.5">Select default accounts to pre-select in logging operations.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
                <div>
                  <label htmlFor="default-income" className="block text-xs text-muted-foreground mb-1">Default Income Account</label>
                  <select
                    id="default-income"
                    value={defaults.income_acc}
                    onChange={async (e) => {
                      const newDefaults = { ...defaults, income_acc: e.target.value };
                      try {
                        const res = await fetch(`${API_URL}/api/v1/config`, {
                          method: 'PUT',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify(newDefaults),
                        });
                        if (!res.ok) throw new Error('Update failed');
                        setDefaults(newDefaults);
                        addToast('success', 'Config updated.');
                      } catch (err: any) {
                        addToast('error', err.message);
                      }
                    }}
                    className="bg-background border border-border text-foreground rounded-md px-3 py-2 text-sm w-full focus:outline-none focus:ring-1 focus:ring-ring"
                  >
                    <option value="">-- None --</option>
                    {accounts.map(acc => (
                      <option key={acc.id} value={acc.id}>{acc.name} ({acc.id})</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="default-expense" className="block text-xs text-muted-foreground mb-1">Default Expense Account</label>
                  <select
                    id="default-expense"
                    value={defaults.expense_acc}
                    onChange={async (e) => {
                      const newDefaults = { ...defaults, expense_acc: e.target.value };
                      try {
                        const res = await fetch(`${API_URL}/api/v1/config`, {
                          method: 'PUT',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify(newDefaults),
                        });
                        if (!res.ok) throw new Error('Update failed');
                        setDefaults(newDefaults);
                        addToast('success', 'Config updated.');
                      } catch (err: any) {
                        addToast('error', err.message);
                      }
                    }}
                    className="bg-background border border-border text-foreground rounded-md px-3 py-2 text-sm w-full focus:outline-none focus:ring-1 focus:ring-ring"
                  >
                    <option value="">-- None --</option>
                    {accounts.map(acc => (
                      <option key={acc.id} value={acc.id}>{acc.name} ({acc.id})</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

          </div>
        )}

        {/* --- TAB: RENDER HISTORY --- */}
        {activeTab === 'history' && (
          <div className="space-y-8">
            <div>
              <h2 className="text-xl font-bold tracking-tight">Audit Archive</h2>
              <p className="text-xs text-muted-foreground mt-1">Review finalized rendering cycle snapshots.</p>
            </div>

            <div className="bg-card border border-border rounded-lg overflow-hidden">
              {renderHistory.length === 0 ? (
                <div className="p-12 text-center text-sm text-muted-foreground">
                  No rendered snapshot history found. Execute a render cycle to populate this section.
                </div>
              ) : (
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-border text-muted-foreground text-[10px] uppercase font-semibold">
                      <th className="p-4">Snapshot ID</th>
                      <th className="p-4">Execution Date</th>
                      <th className="p-4 text-right">Net Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {renderHistory.map((h) => (
                      <tr key={h.id} className="border-b border-border hover:bg-secondary/20 transition-colors">
                        <td className="p-4 font-mono font-bold text-xs">r-{h.id}</td>
                        <td className="p-4 text-muted-foreground text-xs font-mono">{h.rendered_at}</td>
                        <td className={`p-4 text-right font-bold tabular-nums ${h.net_amount >= 0 ? 'text-balanced' : 'text-unbalanced'}`}>
                          {formatCLP(h.net_amount)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

      </main>

      {/* --- NOTIFICATIONS TOAST LAYER --- */}
      <div
        aria-live="polite"
        className="fixed bottom-6 right-6 flex flex-col gap-2 z-50 max-w-sm pointer-events-none"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className="pointer-events-auto bg-card border border-border shadow-lg rounded-md p-4 flex items-center gap-3 text-foreground animate-in slide-in-from-bottom duration-200"
          >
            {toast.type === 'success' ? (
              <CheckCircle2 size={16} className="text-balanced shrink-0" />
            ) : toast.type === 'error' ? (
              <AlertCircle size={16} className="text-unbalanced shrink-0" />
            ) : (
              <Info size={16} className="text-muted-foreground shrink-0" />
            )}
            <span className="text-xs font-medium">{toast.text}</span>
          </div>
        ))}
      </div>

      {/* --- MODAL: CONFIRM RENDER CYCLE --- */}
      {showRenderModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-[2px] flex items-center justify-center z-40 animate-in fade-in duration-150">
          <div className="bg-card border border-border shadow-xl rounded-lg max-w-md w-full p-6 space-y-4 animate-in zoom-in-95 duration-200">
            <h3 className="text-base font-bold flex items-center gap-2">
              <RefreshCw size={16} className="text-primary" />
              <span>Execute Render Audit</span>
            </h3>
            <p className="text-xs text-muted-foreground">
              This process compiles all active transactions, updates the ledger balances, and creates a history snapshot totaling <span className="font-bold tabular-nums">{formatCLP(markedTotal)}</span>. This cannot be undone.
            </p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowRenderModal(false)}
                className="bg-secondary text-secondary-foreground border border-border hover:bg-muted text-xs px-3 py-2 rounded-md font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteRender}
                disabled={isSubmitting}
                className="bg-primary text-primary-foreground text-xs px-3 py-2 rounded-md font-semibold hover:opacity-90 flex items-center gap-1.5"
              >
                {isSubmitting && <Loader2 size={12} className="animate-spin" />}
                <span>Confirm & Render</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --- MODAL: CREATE ACCOUNT --- */}
      {showNewAccountModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-[2px] flex items-center justify-center z-40 animate-in fade-in duration-150">
          <div className="bg-card border border-border shadow-xl rounded-lg max-w-md w-full p-6 space-y-4 animate-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center">
              <h3 className="text-base font-bold">New Account Setup</h3>
              <button onClick={() => setShowNewAccountModal(false)} className="text-muted-foreground hover:text-foreground">
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleCreateAccount} className="space-y-3 text-sm">
              <div>
                <label htmlFor="new-acc-id" className="block text-xs text-muted-foreground mb-1">Short ID (ID used in CLI)</label>
                <input
                  id="new-acc-id"
                  type="text"
                  value={newAccId}
                  onChange={(e) => setNewAccId(e.target.value)}
                  placeholder="e.g. bci, wallet, card"
                  required
                  className="bg-background border border-border text-foreground rounded-md px-3 py-2 text-sm w-full focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>

              <div>
                <label htmlFor="new-acc-name" className="block text-xs text-muted-foreground mb-1">Display Name</label>
                <input
                  id="new-acc-name"
                  type="text"
                  value={newAccName}
                  onChange={(e) => setNewAccName(e.target.value)}
                  placeholder="e.g. Banco de Chile Checking"
                  required
                  className="bg-background border border-border text-foreground rounded-md px-3 py-2 text-sm w-full focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="new-acc-type" className="block text-xs text-muted-foreground mb-1">Type</label>
                  <select
                    id="new-acc-type"
                    value={newAccType}
                    onChange={(e) => setNewAccType(e.target.value as 'debit' | 'credit')}
                    className="bg-background border border-border text-foreground rounded-md px-3 py-2 text-sm w-full focus:outline-none focus:ring-1 focus:ring-ring"
                  >
                    <option value="debit">Debit</option>
                    <option value="credit">Credit</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="new-acc-balance" className="block text-xs text-muted-foreground mb-1">Initial Balance (CLP)</label>
                  <input
                    id="new-acc-balance"
                    type="number"
                    inputMode="numeric"
                    value={newAccBalance}
                    onChange={(e) => setNewAccBalance(e.target.value)}
                    placeholder="0"
                    className="bg-background border border-border text-foreground rounded-md px-3 py-2 text-sm w-full focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                </div>
              </div>

              {newAccType === 'credit' && (
                <div>
                  <label htmlFor="new-acc-limit" className="block text-xs text-muted-foreground mb-1">Credit Card Limit</label>
                  <input
                    id="new-acc-limit"
                    type="number"
                    inputMode="numeric"
                    value={newAccLimit}
                    onChange={(e) => setNewAccLimit(e.target.value)}
                    placeholder="500000"
                    className="bg-background border border-border text-foreground rounded-md px-3 py-2 text-sm w-full focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                </div>
              )}

              {newAccError && (
                <div className="flex items-center gap-2 p-3 bg-destructive/10 border border-destructive text-destructive rounded-md text-xs">
                  <AlertCircle size={14} className="shrink-0" />
                  <span>{newAccError}</span>
                </div>
              )}

              <div className="flex gap-2 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewAccountModal(false)}
                  className="bg-secondary text-secondary-foreground border border-border hover:bg-muted text-xs px-3 py-2 rounded-md font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="bg-primary text-primary-foreground text-xs px-3 py-2 rounded-md font-semibold hover:opacity-90 flex items-center gap-1.5"
                >
                  {isSubmitting && <Loader2 size={12} className="animate-spin" />}
                  <span>Add Ledger</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- MODAL: RENAME LEDGER --- */}
      {showRenameModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-[2px] flex items-center justify-center z-40 animate-in fade-in duration-150">
          <div className="bg-card border border-border shadow-xl rounded-lg max-w-sm w-full p-6 space-y-4 animate-in zoom-in-95 duration-200">
            <h3 className="text-base font-bold">Rename '{showRenameModal.id}'</h3>
            <form onSubmit={handleRenameAccount} className="space-y-4 text-sm">
              <div>
                <label htmlFor="rename-id" className="block text-xs text-muted-foreground mb-1">New ID</label>
                <input
                  id="rename-id"
                  type="text"
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  required
                  className="bg-background border border-border text-foreground rounded-md px-3 py-2 text-sm w-full focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <div className="flex gap-2 justify-end">
                <button
                  type="button"
                  onClick={() => setShowRenameModal(null)}
                  className="bg-secondary text-secondary-foreground border border-border hover:bg-muted text-xs px-3 py-2 rounded-md font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-primary text-primary-foreground text-xs px-3 py-2 rounded-md font-semibold hover:opacity-90"
                >
                  Rename
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- MODAL: UPDATE CREDIT LIMIT --- */}
      {showLimitModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-[2px] flex items-center justify-center z-40 animate-in fade-in duration-150">
          <div className="bg-card border border-border shadow-xl rounded-lg max-w-sm w-full p-6 space-y-4 animate-in zoom-in-95 duration-200">
            <h3 className="text-base font-bold">Credit Limit: {showLimitModal.id}</h3>
            <form onSubmit={handleUpdateLimit} className="space-y-4 text-sm">
              <div>
                <label htmlFor="limit-value" className="block text-xs text-muted-foreground mb-1">New Credit Limit (CLP)</label>
                <input
                  id="limit-value"
                  type="number"
                  inputMode="numeric"
                  value={limitValue}
                  onChange={(e) => setLimitValue(e.target.value)}
                  required
                  className="bg-background border border-border text-foreground rounded-md px-3 py-2 text-sm w-full focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <div className="flex gap-2 justify-end">
                <button
                  type="button"
                  onClick={() => setShowLimitModal(null)}
                  className="bg-secondary text-secondary-foreground border border-border hover:bg-muted text-xs px-3 py-2 rounded-md font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-primary text-primary-foreground text-xs px-3 py-2 rounded-md font-semibold hover:opacity-90"
                >
                  Save Limit
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
