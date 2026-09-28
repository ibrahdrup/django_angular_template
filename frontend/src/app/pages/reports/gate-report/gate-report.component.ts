import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../core/services/api.service';
import { GateAssignmentReportRow } from '../../../core/models/models';

@Component({
  selector: 'app-gate-report',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './gate-report.component.html',
  styleUrl: '../reports.css',
})
export class GateReportComponent {
  fromDate = this.daysAgo(7);
  toDate = this.today();
  gateNumber = '';
  rows = signal<GateAssignmentReportRow[]>([]);
  loading = signal(false);
  error = signal('');
  searched = signal(false);

  constructor(private api: ApiService) {}

  today(): string {
    return new Date().toISOString().slice(0, 10);
  }

  daysAgo(n: number): string {
    const d = new Date();
    d.setDate(d.getDate() - n);
    return d.toISOString().slice(0, 10);
  }

  run() {
    if (!this.fromDate || !this.toDate) {
      this.error.set('Both from_date and to_date are required.');
      return;
    }
    this.loading.set(true);
    this.error.set('');
    this.searched.set(true);
    this.api.gateAssignmentReport(this.fromDate, this.toDate, this.gateNumber || undefined).subscribe({
      next: (res) => {
        this.rows.set(res.results);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(err?.error?.message || 'Failed to load report.');
        this.loading.set(false);
      },
    });
  }

  downloadCsv() {
    this.api.downloadGateAssignmentReportCsv(this.fromDate, this.toDate, this.gateNumber || undefined).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `gate_assignment_report_${this.fromDate}_to_${this.toDate}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: () => this.error.set('Failed to download CSV.'),
    });
  }
}
