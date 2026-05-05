# Sigma: High-Efficiency Finance Tracker

Sigma (`sgm`) is a streamlined, command-line-first financial management system. It prioritizes low-friction data entry via integrations (like Telegram) and professional-grade data visualization via a professional CLI.

---

## 1. Purpose
The primary objective of `sgm` is to bridge the gap between **immediate transaction logging** and **periodic financial reconciliation**. It eliminates the complexity of traditional banking apps by providing a centralized, programmable interface for tracking multiple accounts with a unique "rendering" workflow.

---

## 2. Core Functional Scope

### A. Account Management
*   **Debit Accounts:** Standard tracking of liquid balances.
*   **Credit Cards:** 
    *   Tracking of current debt and available credit.
    *   Management of rolling credit limits (excludes installment/cuota logic).
*   **Transfers:** Direct balance adjustment between accounts (e.g., paying a Credit Card from a Debit account).

### B. Movement Tracking (Income & Expenses)
*   **Logging:** Minimalist entry with description, amount, and account target.
*   **Marking:** Every movement is automatically "marked" for reconciliation upon entry.
*   **Currency:** Standardized for Chilean Pesos (CLP) for initial release.

### C. The Rendering Workflow
This is the core differentiator of the project.
1.  **Selection:** The system identifies all "marked" movements.
2.  **Calculation:** It calculates the net sum ($Incomes - Expenses$).
3.  **Persistence:** The resulting figure is stored in a `render_history` table.
4.  **Reset:** All processed movements are "unmarked."
5.  **Independence:** This process provides a periodic financial snapshot without altering the static account balances.

---

## 3. Technical Architecture

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Language** | Python 3.x | Core logic and automation scripts. |
| **Database** | SQLite | Serverless, single-file relational storage. |
| **CLI Framework** | Typer + Rich | Handles commands and professional UI formatting. |
| **Mobile Entry** | Telegram Bot API | Strict-format input for remote logging. |
| **Deployment** | Linux VM / systemd | 24/7 availability for the bot listener. |

Note: The idea is that is usable just in personal computer CLI. The Telegram+VM is just an option of Sigma reduce friction to the core of Sigma.
---

## 4. User Interfaces

### CLI (Professional Interface)
Built for speed and clarity. It uses tables and panels to display data.

### Telegram Bot (Input Gateway)
Designed for integration.
*   **Security:** Strict `user_id` filtering; only authorized IDs can interact with the database.

---

## 5. System Logic Constraints

*   **Transactional Integrity:** Transfers update account balances immediately; Movements (Inc/Exp) do not affect balances until a separate logic layer is implemented (if desired later), remaining focused on the "Rendering" sum.
*   **Data Retention:** Rendered movements are kept in the database for historical auditing but removed from the "active" marked pool.
*   **Minimalist Metadata:** No categories or tags are required for the initial version; description strings are the primary identifier.

---

## 6. Success Metrics
*   **Entry Speed:** < 5 seconds from transaction to confirmed log via mobile.
*   **Zero-Maintenance:** SQLite and `systemd` setup ensure the VM requires no manual database management.
*   **Auditability:** A clear, permanent record of every "Rendered" period.
