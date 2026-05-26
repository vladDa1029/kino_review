import { useState } from 'react';
import {
  getAdminDocumentDownloadUrl,
  getAdminReport,
  getAdminReportDownloadUrl,
  listAdminShiftReports,
} from '../services/api';

const AdminReportsPage = () => {
  const [shiftId, setShiftId] = useState('');
  const [reportId, setReportId] = useState('');
  const [documentId, setDocumentId] = useState('');
  const [shiftReports, setShiftReports] = useState([]);
  const [reportMeta, setReportMeta] = useState(null);
  const [reportDownloadUrl, setReportDownloadUrl] = useState('');
  const [documentDownloadUrl, setDocumentDownloadUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleShiftLookup = async (event) => {
    event.preventDefault();
    try {
      setLoading(true);
      setError('');
      const response = await listAdminShiftReports(shiftId.trim());
      setShiftReports(response.items || []);
    } catch (err) {
      setError(err.message || 'Не удалось получить отчеты смены');
    } finally {
      setLoading(false);
    }
  };

  const handleReportLookup = async (event) => {
    event.preventDefault();
    try {
      setLoading(true);
      setError('');
      const [meta, download] = await Promise.all([
        getAdminReport(reportId.trim()),
        getAdminReportDownloadUrl(reportId.trim()),
      ]);
      setReportMeta(meta);
      setReportDownloadUrl(download.download_url || '');
    } catch (err) {
      setError(err.message || 'Не удалось получить данные отчета');
    } finally {
      setLoading(false);
    }
  };

  const handleDocumentLookup = async (event) => {
    event.preventDefault();
    try {
      setLoading(true);
      setError('');
      const response = await getAdminDocumentDownloadUrl(documentId.trim());
      setDocumentDownloadUrl(response.download_url || '');
    } catch (err) {
      setError(err.message || 'Не удалось получить ссылку на документ');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="admin-screen admin-content-stack">
      <section className="management-card admin-panel-card">
        <div className="admin-section-header">
          <div>
            <span className="projects-panel-eyebrow">Project admin</span>
            <h2>Отчеты и документы</h2>
            <p>Технический экран для метаданных отчетов и временных ссылок на скачивание.</p>
          </div>
        </div>
      </section>

      {error ? <div className="management-card admin-panel-card error-text">{error}</div> : null}

      <section className="management-card admin-form-stack">
        <form className="stacked-form" onSubmit={handleShiftLookup}>
          <div className="section-heading">
            <div>
              <h3>Отчеты по смене</h3>
              <p>Получение всех версий отчета для `shift_id`.</p>
            </div>
          </div>
          <div className="grid-two-columns admin-toolbar-grid">
            <label className="field-block">
              <span>Shift ID</span>
              <input value={shiftId} onChange={(event) => setShiftId(event.target.value)} required />
            </label>
            <div className="inline-actions admin-form-actions-end">
              <button type="submit" className="profile-save-btn compact" disabled={loading}>
                Загрузить список
              </button>
            </div>
          </div>
        </form>

        {shiftReports.length > 0 ? (
          <div className="table-shell">
            <table className="user-table">
              <thead>
                <tr>
                  <th>Version</th>
                  <th>Generation</th>
                  <th>Actuality</th>
                  <th>File</th>
                  <th>Generated</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {shiftReports.map((item) => (
                  <tr key={item.oid}>
                    <td data-label="Version">{item.version}</td>
                    <td data-label="Generation">{item.generation_status_name}</td>
                    <td data-label="Actuality">{item.actuality_status_name}</td>
                    <td data-label="File">{item.file_name}</td>
                    <td data-label="Generated">{item.generated_at ? new Date(item.generated_at).toLocaleString() : '-'}</td>
                    <td data-label="Error">{item.error_message || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="management-card admin-form-stack">
        <form className="stacked-form" onSubmit={handleReportLookup}>
          <div className="section-heading">
            <div>
              <h3>Метаданные отчета</h3>
              <p>Получение метаданных и ready-download URL для `report_id`.</p>
            </div>
          </div>
          <div className="grid-two-columns admin-toolbar-grid">
            <label className="field-block">
              <span>Report ID</span>
              <input value={reportId} onChange={(event) => setReportId(event.target.value)} required />
            </label>
            <div className="inline-actions admin-form-actions-end">
              <button type="submit" className="profile-save-btn compact" disabled={loading}>
                Загрузить отчет
              </button>
            </div>
          </div>
        </form>

        {reportMeta ? (
          <div className="admin-report-grid">
            <div className="admin-summary-card">
              <span>Project ID</span>
              <strong>{reportMeta.project_id}</strong>
            </div>
            <div className="admin-summary-card">
              <span>Shift ID</span>
              <strong>{reportMeta.shift_id}</strong>
            </div>
            <div className="admin-summary-card">
              <span>File</span>
              <strong>{reportMeta.file_name}</strong>
            </div>
            <div className="admin-summary-card">
              <span>Download URL</span>
              <strong className="admin-break-anywhere">{reportDownloadUrl || '-'}</strong>
            </div>
          </div>
        ) : null}
      </section>

      <section className="management-card admin-form-stack">
        <form className="stacked-form" onSubmit={handleDocumentLookup}>
          <div className="section-heading">
            <div>
              <h3>Ссылка на документ</h3>
              <p>Получение временной ссылки для `document_id`.</p>
            </div>
          </div>
          <div className="grid-two-columns admin-toolbar-grid">
            <label className="field-block">
              <span>Document ID</span>
              <input value={documentId} onChange={(event) => setDocumentId(event.target.value)} required />
            </label>
            <div className="inline-actions admin-form-actions-end">
              <button type="submit" className="profile-save-btn compact" disabled={loading}>
                Получить ссылку
              </button>
            </div>
          </div>
        </form>

        {documentDownloadUrl ? (
          <div className="admin-summary-card">
            <span>Download URL</span>
            <strong className="admin-break-anywhere">{documentDownloadUrl}</strong>
          </div>
        ) : null}
      </section>
    </div>
  );
};

export default AdminReportsPage;
