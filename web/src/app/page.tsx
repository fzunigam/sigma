'use client';

import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  ArrowLeftRight,
  Plus,
  RefreshCw,
  Trash2,
  Settings,
  CreditCard,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Info,
  Calendar,
  X
} from 'lucide-react';

// API BASE URL
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
  // Navigation Tabs
  const [activeTab, setActiveTab] = useState<'dashboard' | 'accounts' | 'history'>('dashboard');

  // Core Data State
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [renderHistory, setRenderHistory] = useState<RenderSnapshot[]>([]);
  const [markedTotal, setMarkedTotal] = useState<number>(0);
  const [netBalance, setNetBalance] = useState<number>(0);
  const [defaults, setDefaults] = useState({ income_acc: '', expense_acc: '' });

  // UI States
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  
  // Modals
  const [showRenderModal, setShowRenderModal] = useState(false);
  const [showNewAccountModal, setShowNewAccountModal] = useState(false);
  const [showRenameModal, setShowRenameModal] = useState<Account | null>(null);
  const [showLimitModal, setShowLimitModal] = useState<Account | null>(null);

  // Forms State
  const [txType, setTxType] = useState<'expense' | 'income' | 'transfer'>('expense');
  const [txAmount, setTxAmount] = useState('');
  const [txDesc, setTxDesc] = useState('');
  const [txAccount, setTxAccount] = useState('');
  const [txTransferTo, setTxTransferTo] = useState('');
  const [txDate, setTxDate] = useState('');
  const [txMark, setTxMark] = useState(true);
  const [txError, setTxError] = useState('');

  // New Account Form
  const [newAccId, setNewAccId] = useState('');
  const [newAccName, setNewAccName] = useState('');
  const [newAccType, setNewAccType] = useState<'debit' | 'credit'>('debit');
  const [newAccBalance, setNewAccBalance] = useState('');
  const [newAccLimit, setNewAccLimit] = useState('');
  const [newAccError, setNewAccError] = useState('');

  // Edit / Limit Modals States
  const [renameValue, setRenameValue] = useState('');
  const [limitValue, setLimitValue] = useState('');

  // Transaction delete double check ID
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Load Status and Configuration
  const fetchData = async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    try {
      // 1. Fetch dashboard status
      const resStatus = await fetch(`${API_URL}/api/v1/status`);
      if (!resStatus.ok) throw new Error('Failed to load status');
      const dataStatus = await resStatus.json();
      setAccounts(dataStatus.accounts || []);
      setMarkedTotal(dataStatus.marked_total || 0);
      setNetBalance(dataStatus.net_balance || 0);

      // 2. Fetch default accounts
      const resConfig = await fetch(`${API_URL}/api/v1/config`);
      if (resConfig.ok) {
        const dataConfig = await resConfig.json();
        setDefaults(dataConfig);
        // Pre-fill form values based on type defaults
        if (txType === 'expense' && dataConfig.expense_acc) {
          setTxAccount(dataConfig.expense_acc);
        } else if (txType === 'income' && dataConfig.income_acc) {
          setTxAccount(dataConfig.income_acc);
        } else if (dataStatus.accounts?.length > 0) {
          setTxAccount(dataStatus.accounts[0].id);
        }
      }

      // 3. Fetch transaction log
      const resTx = await fetch(`${API_URL}/api/v1/transactions?limit=30`);
      if (resTx.ok) {
        setTransactions(await resTx.json());
      }

      // 4. Fetch render history
      const resHist = await fetch(`${API_URL}/api/v1/render/history?limit=20`);
      if (resHist.ok) {
        setRenderHistory(await resHist.json());
      }

    } catch (error: any) {
      addToast('error', error.message || 'Error fetching data from local server.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Update default accounts when transaction type changes
  useEffect(() => {
    if (txType === 'expense' && defaults.expense_acc) {
      setTxAccount(defaults.expense_acc);
    } else if (txType === 'income' && defaults.income_acc) {
      setTxAccount(defaults.income_acc);
    } else if (accounts.length > 0) {
      setTxAccount(accounts[0].id);
    }
  }, [txType, defaults, accounts]);

  // Toast System
  const addToast = (type: 'success' | 'error' | 'info', text: string) => {
    const id = Math.random().toString(36).substr(2, 9);
    setToasts((prev) => [...prev, { id, type, text }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  };

  // Helper formatting for CLP Pesos
  const formatCLP = (amount: number) => {
    const isNegative = amount < 0;
    const absAmount = Math.abs(amount);
    const formatted = new Intl.NumberFormat('es-CL').format(absAmount);
    return `${isNegative ? '-\xa0' : ''}$${formatted}`;
  };

  // Quick Action Submission
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
        // Transfer
        if (!txAccount || !txTransferTo) {
          setTxError('Both source and destination accounts are required.');
          setIsSubmitting(false);
          return;
        }
        if (txAccount === txTransferTo) {
          setTxError('Source and destination accounts must be different.');
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
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to log transaction.');
      }

      addToast('success', `Transaction logged successfully! ID: ${data.id || 'N/A'}`);
      setTxAmount('');
      setTxDesc('');
      setTxDate('');
      setTxError('');
      fetchData(false);
    } catch (err: any) {
      setTxError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete Transaction Action
  const handleDeleteTransaction = async (uniqueId: string) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/transactions/${uniqueId}`, {
        method: 'DELETE',
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to delete transaction.');
      }
      addToast('success', 'Transaction deleted successfully.');
      setDeleteConfirmId(null);
      fetchData(false);
    } catch (err: any) {
      addToast('error', err.message);
    }
  };

  // Render Cycle Action
  const handleExecuteRender = async () => {
    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/render`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Render failed.');
      }
      addToast('success', `Render complete! Logged: ${formatCLP(data.net_amount)} across ${data.count} items.`);
      setShowRenderModal(false);
      fetchData(false);
    } catch (err: any) {
      addToast('error', err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // New Account Action
  const handleCreateAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    setNewAccError('');

    if (!newAccId.trim() || !newAccName.trim()) {
      setNewAccError('Account ID and Name are required.');
      return;
    }

    const initBal = parseInt(newAccBalance, 10) || 0;
    const limit = parseInt(newAccLimit, 10) || 0;

    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/accounts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: newAccId.trim(),
          name: newAccName.trim(),
          type: newAccType,
          initial_balance: initBal,
          credit_limit: limit,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to create account.');
      }

      addToast('success', `Account '${data.account.name}' created!`);
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

  // Rename Account Action
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
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to rename account.');
      }
      addToast('success', `Account renamed to '${data.account.id}' successfully!`);
      setShowRenameModal(null);
      setRenameValue('');
      fetchData(false);
    } catch (err: any) {
      addToast('error', err.message);
    }
  };

  // Update Limit Action
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
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to update credit limit.');
      }
      addToast('success', `Credit limit for '${data.account.id}' updated!`);
      setShowLimitModal(null);
      setLimitValue('');
      fetchData(false);
    } catch (err: any) {
      addToast('error', err.message);
    }
  };

  // Delete Account Action
  const handleDeleteAccount = async (id: string) => {
    if (!confirm(`Are you sure you want to delete account '${id}'? This will preserve transaction history under a ghost account.`)) return;

    try {
      const res = await fetch(`${API_URL}/api/v1/accounts/${id}`, { method: 'DELETE' });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to delete account.');
      }
      addToast('success', `Account '${id}' deleted.`);
      fetchData(false);
    } catch (err: any) {
      addToast('error', err.message);
    }
  };

  return (
    <div className="app-container">
      {/* 1. Sidebar Navigation */}
      <aside style={{ backgroundColor: 'var(--bg-sidebar)', borderRight: '1px solid var(--border-card)', padding: '2rem 1.5rem', display: 'flex', flexDirection: 'column' }}>
        <div style={{ marginBottom: '2.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-emerald))', width: '32px', height: '32px', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ fontFamily: 'Outfit', fontWeight: 800, fontSize: '1.25rem', color: '#000' }}>Σ</span>
          </div>
          <div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>Sigma</h1>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Finance Tracker v0.2.1</span>
          </div>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1 }}>
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`glass-panel ${activeTab === 'dashboard' ? 'active-tab' : ''}`}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              width: '100%',
              textAlign: 'left',
              padding: '0.75rem 1rem',
              background: activeTab === 'dashboard' ? 'var(--accent-cyan-glow)' : 'transparent',
              borderColor: activeTab === 'dashboard' ? 'var(--accent-cyan)' : 'transparent',
              color: activeTab === 'dashboard' ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
              cursor: 'pointer'
            }}
          >
            <TrendingUp size={18} />
            <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>Dashboard</span>
          </button>
          <button
            onClick={() => setActiveTab('accounts')}
            className={`glass-panel ${activeTab === 'accounts' ? 'active-tab' : ''}`}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              width: '100%',
              textAlign: 'left',
              padding: '0.75rem 1rem',
              background: activeTab === 'accounts' ? 'var(--accent-cyan-glow)' : 'transparent',
              borderColor: activeTab === 'accounts' ? 'var(--accent-cyan)' : 'transparent',
              color: activeTab === 'accounts' ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
              cursor: 'pointer'
            }}
          >
            <CreditCard size={18} />
            <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>Accounts</span>
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`glass-panel ${activeTab === 'history' ? 'active-tab' : ''}`}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              width: '100%',
              textAlign: 'left',
              padding: '0.75rem 1rem',
              background: activeTab === 'history' ? 'var(--accent-cyan-glow)' : 'transparent',
              borderColor: activeTab === 'history' ? 'var(--accent-cyan)' : 'transparent',
              color: activeTab === 'history' ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
              cursor: 'pointer'
            }}
          >
            <FileText size={18} />
            <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>Render History</span>
          </button>
        </nav>

        <div style={{ marginTop: 'auto', padding: '1rem', borderTop: '1px solid var(--border-card)', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <div style={{ background: '#1e293b', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: isLoading ? 'var(--accent-rose)' : 'var(--accent-emerald)' }}></div>
          <span style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
            {isLoading ? 'Syncing…' : 'Local Node Connected'}
          </span>
          <button
            onClick={() => fetchData(true)}
            aria-label="Reload data"
            style={{ marginLeft: 'auto', background: 'transparent', border: 'none', color: 'var(--color-text-secondary)', cursor: 'pointer' }}
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          </button>
        </div>
      </aside>

      {/* 2. Main content container */}
      <main style={{ padding: '2.5rem', overflowY: 'auto', height: '100vh' }} className="animate-slide-up">
        {/* Global Loading Spinner */}
        {isLoading && (
          <div style={{ position: 'fixed', top: '1.5rem', right: '1.5rem', background: '#1e293b', padding: '0.5rem 1rem', borderRadius: '20px', border: '1px solid var(--border-card)', display: 'flex', alignItems: 'center', gap: '0.5rem', zIndex: 100 }}>
            <Loader2 size={14} className="animate-spin text-cyan" />
            <span style={{ fontSize: '0.8rem' }}>Syncing…</span>
          </div>
        )}

        {/* --- TAB: DASHBOARD --- */}
        {activeTab === 'dashboard' && (
          <div>
            {/* Header / Net Balance and Render Banner */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '1.5rem', marginBottom: '2.5rem', alignItems: 'stretch' }}>
              <div className="glass-panel" style={{ background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.4))', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Net Available Balance</span>
                <h2 style={{ fontSize: '3rem', fontWeight: 800, margin: '0.5rem 0', color: netBalance >= 0 ? 'var(--color-text-primary)' : 'var(--accent-rose)' }} className="tabular-nums">
                  {formatCLP(netBalance)}
                </h2>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-text-secondary)', fontSize: '0.85rem' }}>
                  <Info size={14} />
                  <span>Total funds across debit accounts minus outstanding credit card debt.</span>
                </div>
              </div>

              {/* Render Status Card */}
              <div className="glass-panel" style={{ border: '1px solid var(--border-card-hover)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <span style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>Pending marked total</span>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', marginTop: '0.25rem' }}>
                    <span style={{ fontSize: '1.75rem', fontWeight: 700, color: markedTotal === 0 ? 'var(--color-text-secondary)' : markedTotal > 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)' }} className="tabular-nums">
                      {formatCLP(markedTotal)}
                    </span>
                  </div>
                </div>

                <div style={{ marginTop: '1.5rem' }}>
                  <button
                    onClick={() => setShowRenderModal(true)}
                    disabled={markedTotal === 0}
                    style={{
                      width: '100%',
                      background: markedTotal === 0 ? '#1e293b' : 'linear-gradient(135deg, var(--accent-cyan), var(--accent-emerald))',
                      color: markedTotal === 0 ? 'var(--color-text-muted)' : '#000',
                      border: 'none',
                      padding: '0.75rem',
                      borderRadius: '8px',
                      fontWeight: 600,
                      cursor: markedTotal === 0 ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.5rem',
                      transition: 'transform 150ms ease'
                    }}
                  >
                    <RefreshCw size={16} />
                    <span>Render Cycle</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Quick Actions Logger & Account Summary Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '2rem', marginBottom: '2.5rem', alignItems: 'start' }}>
              {/* Left Column: Accounts and Transactions */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                
                {/* Accounts Horizontal List */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <h3 style={{ fontSize: '1.15rem' }}>Your Accounts</h3>
                    <button
                      onClick={() => setShowNewAccountModal(true)}
                      style={{ background: 'transparent', border: 'none', color: 'var(--accent-cyan)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.85rem', fontWeight: 500 }}
                    >
                      <Plus size={16} />
                      Add Account
                    </button>
                  </div>

                  {accounts.length === 0 ? (
                    <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                      No accounts registered. Click "Add Account" to configure your first account.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '1rem' }}>
                      {accounts.map((acc) => (
                        <div key={acc.id} className="glass-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '130px' }}>
                          <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <span style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{acc.id}</span>
                              <span style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem', borderRadius: '4px', background: acc.type === 'credit' ? 'var(--accent-rose-glow)' : 'var(--accent-emerald-glow)', color: acc.type === 'credit' ? 'var(--accent-rose)' : 'var(--accent-emerald)' }}>
                                {acc.type}
                              </span>
                            </div>
                            <h4 style={{ fontSize: '1.05rem', margin: '0.25rem 0' }}>{acc.name}</h4>
                          </div>

                          <div style={{ marginTop: '1rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                              <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Balance</span>
                              <span style={{ fontSize: '1.25rem', fontWeight: 700 }} className="tabular-nums">
                                {formatCLP(acc.balance)}
                              </span>
                            </div>

                            {/* Limit Utilization Progress Bar for Credit accounts */}
                            {acc.type === 'credit' && acc.credit_limit > 0 && (
                              <div style={{ marginTop: '0.5rem' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--color-text-muted)', marginBottom: '0.25rem' }}>
                                  <span>Utilized: {Math.round((acc.balance / acc.credit_limit) * 100)}%</span>
                                  <span>Limit: {formatCLP(acc.credit_limit)}</span>
                                </div>
                                <div style={{ height: '4px', background: '#1e293b', borderRadius: '2px', overflow: 'hidden' }}>
                                  <div style={{ height: '100%', width: `${Math.min((acc.balance / acc.credit_limit) * 100, 100)}%`, background: 'var(--accent-rose)' }}></div>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Recent Transaction Log Table */}
                <div>
                  <h3 style={{ fontSize: '1.15rem', marginBottom: '1rem' }}>Recent Log activity</h3>
                  <div className="glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
                    {transactions.length === 0 ? (
                      <div style={{ padding: '2.5rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                        No transactions registered yet. Use the Quick Logger to add entries.
                      </div>
                    ) : (
                      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
                        <thead>
                          <tr style={{ borderBottom: '1px solid var(--border-card)', color: 'var(--color-text-secondary)', fontSize: '0.8rem', textTransform: 'uppercase' }}>
                            <th style={{ padding: '1rem' }}>Type</th>
                            <th style={{ padding: '1rem' }}>Description</th>
                            <th style={{ padding: '1rem' }}>Account</th>
                            <th style={{ padding: '1rem', textAlign: 'right' }}>Amount</th>
                            <th style={{ padding: '1rem', width: '100px' }}>Date</th>
                            <th style={{ padding: '1rem', width: '80px', textAlign: 'center' }}>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {transactions.map((tx) => (
                            <tr key={tx.unique_id} style={{ borderBottom: '1px solid var(--border-card)' }}>
                              <td style={{ padding: '1rem', textTransform: 'capitalize' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                  {tx.type === 'income' ? (
                                    <TrendingUp size={16} className="text-emerald" />
                                  ) : tx.type === 'expense' ? (
                                    <TrendingDown size={16} className="text-rose" />
                                  ) : (
                                    <ArrowLeftRight size={16} className="text-cyan" />
                                  )}
                                  <span>{tx.type}</span>
                                </div>
                              </td>
                              <td style={{ padding: '1rem', fontWeight: 500 }}>{tx.description}</td>
                              <td style={{ padding: '1rem', color: 'var(--color-text-secondary)' }} className="tabular-nums">{tx.account_id || '—'}</td>
                              <td style={{ padding: '1rem', textAlign: 'right', fontWeight: 600, color: tx.type === 'income' ? 'var(--accent-emerald)' : tx.type === 'expense' ? 'var(--accent-rose)' : 'var(--accent-cyan)' }} className="tabular-nums">
                                {tx.type === 'expense' ? '-' : ''}{formatCLP(tx.amount)}
                              </td>
                              <td style={{ padding: '1rem', color: 'var(--color-text-muted)' }}>{tx.created_at.substring(0, 10)}</td>
                              <td style={{ padding: '1rem', textAlign: 'center' }}>
                                {deleteConfirmId === tx.unique_id ? (
                                  <div style={{ display: 'flex', gap: '0.25rem', justifyContent: 'center' }}>
                                    <button
                                      onClick={() => handleDeleteTransaction(tx.unique_id)}
                                      aria-label="Confirm delete"
                                      style={{ background: 'var(--accent-rose)', border: 'none', borderRadius: '4px', color: '#fff', fontSize: '0.7rem', padding: '0.2rem 0.4rem', cursor: 'pointer' }}
                                    >
                                      Delete
                                    </button>
                                    <button
                                      onClick={() => setDeleteConfirmId(null)}
                                      aria-label="Cancel delete"
                                      style={{ background: '#475569', border: 'none', borderRadius: '4px', color: '#fff', fontSize: '0.7rem', padding: '0.2rem 0.4rem', cursor: 'pointer' }}
                                    >
                                      Cancel
                                    </button>
                                  </div>
                                ) : (
                                  <button
                                    onClick={() => setDeleteConfirmId(tx.unique_id)}
                                    aria-label={`Delete transaction ${tx.unique_id}`}
                                    style={{ background: 'transparent', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', transition: 'color var(--transition-normal)' }}
                                    onMouseOver={(e) => (e.currentTarget.style.color = 'var(--accent-rose)')}
                                    onMouseOut={(e) => (e.currentTarget.style.color = 'var(--color-text-muted)')}
                                  >
                                    <Trash2 size={15} />
                                  </button>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>
              </div>

              {/* Right Column: Tabbed Quick Logger */}
              <div className="glass-panel" style={{ border: '1px solid var(--border-card-hover)', position: 'sticky', top: '2.5rem' }}>
                <h3 style={{ fontSize: '1.15rem', marginBottom: '1.25rem' }}>Quick Logger</h3>

                {/* Tabs selection */}
                <div style={{ display: 'flex', background: '#0f172a', padding: '0.25rem', borderRadius: '8px', marginBottom: '1.5rem' }}>
                  <button
                    onClick={() => setTxType('expense')}
                    style={{ flex: 1, border: 'none', background: txType === 'expense' ? '#1e293b' : 'transparent', color: txType === 'expense' ? 'var(--accent-rose)' : 'var(--color-text-secondary)', padding: '0.5rem', borderRadius: '6px', cursor: 'pointer', fontWeight: 500, fontSize: '0.85rem' }}
                  >
                    Expense
                  </button>
                  <button
                    onClick={() => setTxType('income')}
                    style={{ flex: 1, border: 'none', background: txType === 'income' ? '#1e293b' : 'transparent', color: txType === 'income' ? 'var(--accent-emerald)' : 'var(--color-text-secondary)', padding: '0.5rem', borderRadius: '6px', cursor: 'pointer', fontWeight: 500, fontSize: '0.85rem' }}
                  >
                    Income
                  </button>
                  <button
                    onClick={() => setTxType('transfer')}
                    style={{ flex: 1, border: 'none', background: txType === 'transfer' ? '#1e293b' : 'transparent', color: txType === 'transfer' ? 'var(--accent-cyan)' : 'var(--color-text-secondary)', padding: '0.5rem', borderRadius: '6px', cursor: 'pointer', fontWeight: 500, fontSize: '0.85rem' }}
                  >
                    Transfer
                  </button>
                </div>

                <form onSubmit={handleLogTransaction} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  
                  {/* Amount Input */}
                  <div>
                    <label htmlFor="tx-amount" style={{ display: 'block', fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '0.25rem' }}>Amount (CLP)</label>
                    <input
                      id="tx-amount"
                      type="number"
                      inputMode="numeric"
                      value={txAmount}
                      onChange={(e) => setTxAmount(e.target.value)}
                      placeholder="e.g. 5000…"
                      required
                      style={{ width: '100%', background: '#0f172a', border: '1px solid var(--border-card)', borderRadius: '6px', padding: '0.6rem', color: '#fff', fontSize: '0.95rem' }}
                    />
                  </div>

                  {/* Description Input */}
                  <div>
                    <label htmlFor="tx-desc" style={{ display: 'block', fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '0.25rem' }}>Description</label>
                    <input
                      id="tx-desc"
                      type="text"
                      value={txDesc}
                      onChange={(e) => setTxDesc(e.target.value)}
                      placeholder="e.g. Lunch, Coffee, Rent…"
                      required
                      style={{ width: '100%', background: '#0f172a', border: '1px solid var(--border-card)', borderRadius: '6px', padding: '0.6rem', color: '#fff', fontSize: '0.95rem' }}
                    />
                  </div>

                  {/* Account Selector (Or Source Account for transfers) */}
                  <div>
                    <label htmlFor="tx-account" style={{ display: 'block', fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '0.25rem' }}>
                      {txType === 'transfer' ? 'Source Account' : 'Account'}
                    </label>
                    <select
                      id="tx-account"
                      value={txAccount}
                      onChange={(e) => setTxAccount(e.target.value)}
                      style={{ width: '100%', background: '#0f172a', border: '1px solid var(--border-card)', borderRadius: '6px', padding: '0.6rem', color: '#fff', fontSize: '0.95rem' }}
                    >
                      {accounts.map((acc) => (
                        <option key={acc.id} value={acc.id}>{acc.name} ({acc.id})</option>
                      ))}
                    </select>
                  </div>

                  {/* Target Account (Only for transfers) */}
                  {txType === 'transfer' && (
                    <div>
                      <label htmlFor="tx-transfer-to" style={{ display: 'block', fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '0.25rem' }}>Destination Account</label>
                      <select
                        id="tx-transfer-to"
                        value={txTransferTo}
                        onChange={(e) => setTxTransferTo(e.target.value)}
                        style={{ width: '100%', background: '#0f172a', border: '1px solid var(--border-card)', borderRadius: '6px', padding: '0.6rem', color: '#fff', fontSize: '0.95rem' }}
                      >
                        <option value="">-- Choose Account --</option>
                        {accounts.map((acc) => (
                          <option key={acc.id} value={acc.id}>{acc.name} ({acc.id})</option>
                        ))}
                      </select>
                    </div>
                  )}

                  {/* Custom Date Selector */}
                  <div>
                    <label htmlFor="tx-date" style={{ display: 'block', fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '0.25rem' }}>Date (Optional)</label>
                    <div style={{ position: 'relative' }}>
                      <input
                        id="tx-date"
                        type="date"
                        value={txDate}
                        onChange={(e) => setTxDate(e.target.value)}
                        style={{ width: '100%', background: '#0f172a', border: '1px solid var(--border-card)', borderRadius: '6px', padding: '0.6rem', color: '#fff', fontSize: '0.95rem' }}
                      />
                    </div>
                  </div>

                  {/* Mark toggle (only for Income/Expense) */}
                  {txType !== 'transfer' && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.25rem 0' }}>
                      <input
                        id="tx-mark"
                        type="checkbox"
                        checked={txMark}
                        onChange={(e) => setTxMark(e.target.checked)}
                        style={{ width: '16px', height: '16px', accentColor: 'var(--accent-cyan)' }}
                      />
                      <label htmlFor="tx-mark" style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', cursor: 'pointer' }}>Mark for review cycle</label>
                    </div>
                  )}

                  {/* Inline Error */}
                  {txError && (
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', background: 'var(--accent-rose-glow)', border: '1px solid var(--accent-rose)', borderRadius: '6px', padding: '0.6rem', color: 'var(--accent-rose)', fontSize: '0.8rem' }}>
                      <AlertCircle size={16} style={{ flexShrink: 0 }} />
                      <span>{txError}</span>
                    </div>
                  )}

                  {/* Submit Button */}
                  <button
                    type="submit"
                    disabled={isSubmitting || accounts.length === 0}
                    style={{
                      marginTop: '0.5rem',
                      background: accounts.length === 0 ? '#1e293b' : txType === 'expense' ? 'var(--accent-rose)' : txType === 'income' ? 'var(--accent-emerald)' : 'var(--accent-cyan)',
                      color: accounts.length === 0 ? 'var(--color-text-muted)' : '#000',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '0.75rem',
                      fontWeight: 600,
                      cursor: (isSubmitting || accounts.length === 0) ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      justifyContent: 'center',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}
                  >
                    {isSubmitting && <Loader2 size={16} className="animate-spin" />}
                    <span>{isSubmitting ? 'Logging…' : `Log ${txType.charAt(0).toUpperCase() + txType.slice(1)}`}</span>
                  </button>
                </form>
              </div>
            </div>
          </div>
        )}

        {/* --- TAB: ACCOUNTS MANAGEMENT --- */}
        {activeTab === 'accounts' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
              <div>
                <h2 style={{ fontSize: '1.5rem', marginBottom: '0.25rem' }}>Accounts Config</h2>
                <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>Configure debit accounts, credit cards, limits, and defaults.</p>
              </div>
              <button
                onClick={() => setShowNewAccountModal(true)}
                style={{ background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-emerald))', border: 'none', color: '#000', padding: '0.6rem 1.2rem', borderRadius: '6px', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
              >
                <Plus size={16} />
                Create Account
              </button>
            </div>

            {/* List Table of Accounts */}
            <div className="glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
              {accounts.length === 0 ? (
                <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                  No accounts found. Click "Create Account" to get started.
                </div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.95rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-card)', color: 'var(--color-text-secondary)', fontSize: '0.8rem', textTransform: 'uppercase' }}>
                      <th style={{ padding: '1.25rem' }}>Account ID</th>
                      <th style={{ padding: '1.25rem' }}>Name</th>
                      <th style={{ padding: '1.25rem' }}>Type</th>
                      <th style={{ padding: '1.25rem', textAlign: 'right' }}>Balance</th>
                      <th style={{ padding: '1.25rem', textAlign: 'right' }}>Credit Limit</th>
                      <th style={{ padding: '1.25rem', textAlign: 'center', width: '240px' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {accounts.map((acc) => (
                      <tr key={acc.id} style={{ borderBottom: '1px solid var(--border-card)' }}>
                        <td style={{ padding: '1.25rem', fontWeight: 600 }} className="tabular-nums">{acc.id}</td>
                        <td style={{ padding: '1.25rem' }}>{acc.name}</td>
                        <td style={{ padding: '1.25rem' }}>
                          <span style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem', borderRadius: '4px', background: acc.type === 'credit' ? 'var(--accent-rose-glow)' : 'var(--accent-emerald-glow)', color: acc.type === 'credit' ? 'var(--accent-rose)' : 'var(--accent-emerald)', textTransform: 'uppercase', fontWeight: 600 }}>
                            {acc.type}
                          </span>
                        </td>
                        <td style={{ padding: '1.25rem', textAlign: 'right', fontWeight: 600 }} className="tabular-nums">{formatCLP(acc.balance)}</td>
                        <td style={{ padding: '1.25rem', textAlign: 'right', color: acc.type === 'credit' ? 'var(--color-text-primary)' : 'var(--color-text-muted)' }} className="tabular-nums">
                          {acc.type === 'credit' ? formatCLP(acc.credit_limit) : '—'}
                        </td>
                        <td style={{ padding: '1.25rem', textAlign: 'center' }}>
                          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                            <button
                              onClick={() => {
                                setRenameValue(acc.id);
                                setShowRenameModal(acc);
                              }}
                              style={{ background: '#1e293b', border: '1px solid var(--border-card)', color: 'var(--color-text-secondary)', padding: '0.4rem 0.8rem', borderRadius: '4px', fontSize: '0.8rem', cursor: 'pointer' }}
                            >
                              Rename
                            </button>
                            {acc.type === 'credit' && (
                              <button
                                onClick={() => {
                                  setLimitValue(acc.credit_limit.toString());
                                  setShowLimitModal(acc);
                                }}
                                style={{ background: '#1e293b', border: '1px solid var(--border-card)', color: 'var(--color-text-secondary)', padding: '0.4rem 0.8rem', borderRadius: '4px', fontSize: '0.8rem', cursor: 'pointer' }}
                              >
                                Limit
                              </button>
                            )}
                            <button
                              onClick={() => handleDeleteAccount(acc.id)}
                              style={{ background: 'var(--accent-rose-glow)', border: '1px solid var(--accent-rose)', color: 'var(--accent-rose)', padding: '0.4rem 0.8rem', borderRadius: '4px', fontSize: '0.8rem', cursor: 'pointer' }}
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

            {/* Default Accounts Setup Panel */}
            <div className="glass-panel" style={{ marginTop: '2.5rem' }}>
              <h3 style={{ fontSize: '1.15rem', marginBottom: '0.5rem' }}>Default User Settings</h3>
              <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>Select default accounts for logging income and expenses quickly.</p>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                <div>
                  <label htmlFor="default-income" style={{ display: 'block', fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '0.5rem' }}>Default Income Account</label>
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
                        if (!res.ok) throw new Error('Failed to update config');
                        setDefaults(newDefaults);
                        addToast('success', 'Default income account updated.');
                      } catch (err: any) {
                        addToast('error', err.message);
                      }
                    }}
                    style={{ width: '100%', background: '#0f172a', border: '1px solid var(--border-card)', borderRadius: '6px', padding: '0.6rem', color: '#fff' }}
                  >
                    <option value="">-- None --</option>
                    {accounts.map(acc => (
                      <option key={acc.id} value={acc.id}>{acc.name} ({acc.id})</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="default-expense" style={{ display: 'block', fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '0.5rem' }}>Default Expense Account</label>
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
                        if (!res.ok) throw new Error('Failed to update config');
                        setDefaults(newDefaults);
                        addToast('success', 'Default expense account updated.');
                      } catch (err: any) {
                        addToast('error', err.message);
                      }
                    }}
                    style={{ width: '100%', background: '#0f172a', border: '1px solid var(--border-card)', borderRadius: '6px', padding: '0.6rem', color: '#fff' }}
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
          <div>
            <h2 style={{ fontSize: '1.5rem', marginBottom: '0.25rem' }}>Historical Audit Snapshots</h2>
            <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem', marginBottom: '2rem' }}>Review all completed render cycle events.</p>

            <div className="glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
              {renderHistory.length === 0 ? (
                <div style={{ padding: '4rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                  No render snapshots recorded. Complete your first cycle in the Dashboard to generate snapshots.
                </div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.95rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-card)', color: 'var(--color-text-secondary)', fontSize: '0.8rem', textTransform: 'uppercase' }}>
                      <th style={{ padding: '1.25rem' }}>Snapshot ID</th>
                      <th style={{ padding: '1.25rem' }}>Rendered Date</th>
                      <th style={{ padding: '1.25rem', textAlign: 'right' }}>Net Sum Processed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {renderHistory.map((h) => (
                      <tr key={h.id} style={{ borderBottom: '1px solid var(--border-card)' }}>
                        <td style={{ padding: '1.25rem', fontWeight: 600 }} className="tabular-nums">r-{h.id}</td>
                        <td style={{ padding: '1.25rem', color: 'var(--color-text-secondary)' }}>{h.rendered_at}</td>
                        <td style={{ padding: '1.25rem', textAlign: 'right', fontWeight: 700, color: h.net_amount >= 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)' }} className="tabular-nums">
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

      {/* --- TOAST ALERTS SYSTEM (aria-live="polite") --- */}
      <div
        aria-live="polite"
        style={{ position: 'fixed', bottom: '1.5rem', right: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem', zIndex: 1000, maxWidth: '350px' }}
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            style={{
              background: '#1e293b',
              borderLeft: `4px solid ${toast.type === 'success' ? 'var(--accent-emerald)' : toast.type === 'error' ? 'var(--accent-rose)' : 'var(--accent-cyan)'}`,
              boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.4)',
              borderRadius: '6px',
              padding: '1rem',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              animation: 'slideUp 200ms ease forwards'
            }}
          >
            {toast.type === 'success' ? (
              <CheckCircle2 className="text-emerald" size={20} style={{ flexShrink: 0 }} />
            ) : toast.type === 'error' ? (
              <AlertCircle className="text-rose" size={20} style={{ flexShrink: 0 }} />
            ) : (
              <Info className="text-cyan" size={20} style={{ flexShrink: 0 }} />
            )}
            <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>{toast.text}</span>
          </div>
        ))}
      </div>

      {/* --- MODAL: RENDER CONFIRMATION --- */}
      {showRenderModal && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0, 0, 0, 0.8)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900 }}>
          <div className="glass-panel" style={{ width: '420px', background: '#0f172a', border: '1px solid var(--border-card-hover)', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.5)', padding: '2rem' }}>
            <h3 style={{ fontSize: '1.25rem', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <RefreshCw size={20} className="text-cyan" />
              <span>Confirm Render Cycle</span>
            </h3>
            <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
              This will lock the current marked movements and sum their values. The marked balance will reset, and a historical snapshot of <strong className="tabular-nums" style={{ color: markedTotal >= 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>{formatCLP(markedTotal)}</strong> will be saved.
            </p>
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowRenderModal(false)}
                style={{ background: 'transparent', border: '1px solid var(--border-card)', borderRadius: '6px', color: 'var(--color-text-secondary)', padding: '0.6rem 1.2rem', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteRender}
                disabled={isSubmitting}
                style={{ background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-emerald))', border: 'none', borderRadius: '6px', color: '#000', padding: '0.6rem 1.2rem', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
              >
                {isSubmitting && <Loader2 size={16} className="animate-spin" />}
                <span>Execute Render</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --- MODAL: NEW ACCOUNT --- */}
      {showNewAccountModal && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0, 0, 0, 0.8)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900 }}>
          <div className="glass-panel" style={{ width: '450px', background: '#0f172a', border: '1px solid var(--border-card-hover)', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.5)', padding: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3 style={{ fontSize: '1.25rem' }}>Add New Account</h3>
              <button
                onClick={() => setShowNewAccountModal(false)}
                aria-label="Close modal"
                style={{ background: 'transparent', border: 'none', color: 'var(--color-text-secondary)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleCreateAccount} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label htmlFor="new-acc-id" style={{ display: 'block', fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '0.25rem' }}>Account ID (Unique Short Name)</label>
                <input
                  id="new-acc-id"
                  type="text"
                  value={newAccId}
                  onChange={(e) => setNewAccId(e.target.value)}
                  placeholder="e.g. wallet, cc, bank…"
                  required
                  style={{ width: '100%', background: '#050b14', border: '1px solid var(--border-card)', borderRadius: '6px', padding: '0.6rem', color: '#fff' }}
                />
              </div>

              <div>
                <label htmlFor="new-acc-name" style={{ display: 'block', fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '0.25rem' }}>Account Display Name</label>
                <input
                  id="new-acc-name"
                  type="text"
                  value={newAccName}
                  onChange={(e) => setNewAccName(e.target.value)}
                  placeholder="e.g. Visa Signature, Wallet Cash…"
                  required
                  style={{ width: '100%', background: '#050b14', border: '1px solid var(--border-card)', borderRadius: '6px', padding: '0.6rem', color: '#fff' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <label htmlFor="new-acc-type" style={{ display: 'block', fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '0.25rem' }}>Account Type</label>
                  <select
                    id="new-acc-type"
                    value={newAccType}
                    onChange={(e) => setNewAccType(e.target.value as 'debit' | 'credit')}
                    style={{ width: '100%', background: '#050b14', border: '1px solid var(--border-card)', borderRadius: '6px', padding: '0.6rem', color: '#fff' }}
                  >
                    <option value="debit">Debit</option>
                    <option value="credit">Credit</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="new-acc-balance" style={{ display: 'block', fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '0.25rem' }}>Initial Balance (CLP)</label>
                  <input
                    id="new-acc-balance"
                    type="number"
                    inputMode="numeric"
                    value={newAccBalance}
                    onChange={(e) => setNewAccBalance(e.target.value)}
                    placeholder="e.g. 100000"
                    style={{ width: '100%', background: '#050b14', border: '1px solid var(--border-card)', borderRadius: '6px', padding: '0.6rem', color: '#fff' }}
                  />
                </div>
              </div>

              {newAccType === 'credit' && (
                <div>
                  <label htmlFor="new-acc-limit" style={{ display: 'block', fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '0.25rem' }}>Credit Limit (CLP)</label>
                  <input
                    id="new-acc-limit"
                    type="number"
                    inputMode="numeric"
                    value={newAccLimit}
                    onChange={(e) => setNewAccLimit(e.target.value)}
                    placeholder="e.g. 500000"
                    style={{ width: '100%', background: '#050b14', border: '1px solid var(--border-card)', borderRadius: '6px', padding: '0.6rem', color: '#fff' }}
                  />
                </div>
              )}

              {newAccError && (
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', background: 'var(--accent-rose-glow)', border: '1px solid var(--accent-rose)', borderRadius: '6px', padding: '0.6rem', color: 'var(--accent-rose)', fontSize: '0.8rem' }}>
                  <AlertCircle size={16} style={{ flexShrink: 0 }} />
                  <span>{newAccError}</span>
                </div>
              )}

              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '1rem' }}>
                <button
                  type="button"
                  onClick={() => setShowNewAccountModal(false)}
                  style={{ background: 'transparent', border: '1px solid var(--border-card)', borderRadius: '6px', color: 'var(--color-text-secondary)', padding: '0.6rem 1.2rem', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  style={{ background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-emerald))', border: 'none', borderRadius: '6px', color: '#000', padding: '0.6rem 1.2rem', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                >
                  {isSubmitting && <Loader2 size={16} className="animate-spin" />}
                  <span>Create Account</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- MODAL: RENAME ACCOUNT --- */}
      {showRenameModal && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0, 0, 0, 0.8)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900 }}>
          <div className="glass-panel" style={{ width: '400px', background: '#0f172a', border: '1px solid var(--border-card-hover)', padding: '2rem' }}>
            <h3 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>Rename Account '{showRenameModal.id}'</h3>
            <form onSubmit={handleRenameAccount} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label htmlFor="rename-id" style={{ display: 'block', fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '0.25rem' }}>New Account ID</label>
                <input
                  id="rename-id"
                  type="text"
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  required
                  style={{ width: '100%', background: '#050b14', border: '1px solid var(--border-card)', borderRadius: '6px', padding: '0.6rem', color: '#fff' }}
                />
              </div>
              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => setShowRenameModal(null)}
                  style={{ background: 'transparent', border: '1px solid var(--border-card)', borderRadius: '6px', color: 'var(--color-text-secondary)', padding: '0.6rem 1.2rem', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{ background: 'var(--accent-cyan)', border: 'none', borderRadius: '6px', color: '#000', padding: '0.6rem 1.2rem', fontWeight: 600, cursor: 'pointer' }}
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
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0, 0, 0, 0.8)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900 }}>
          <div className="glass-panel" style={{ width: '400px', background: '#0f172a', border: '1px solid var(--border-card-hover)', padding: '2rem' }}>
            <h3 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>Update Credit Limit for '{showLimitModal.id}'</h3>
            <form onSubmit={handleUpdateLimit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label htmlFor="limit-value" style={{ display: 'block', fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '0.25rem' }}>New Credit Limit (CLP)</label>
                <input
                  id="limit-value"
                  type="number"
                  inputMode="numeric"
                  value={limitValue}
                  onChange={(e) => setLimitValue(e.target.value)}
                  required
                  style={{ width: '100%', background: '#050b14', border: '1px solid var(--border-card)', borderRadius: '6px', padding: '0.6rem', color: '#fff' }}
                />
              </div>
              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => setShowLimitModal(null)}
                  style={{ background: 'transparent', border: '1px solid var(--border-card)', borderRadius: '6px', color: 'var(--color-text-secondary)', padding: '0.6rem 1.2rem', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{ background: 'var(--accent-cyan)', border: 'none', borderRadius: '6px', color: '#000', padding: '0.6rem 1.2rem', fontWeight: 600, cursor: 'pointer' }}
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
