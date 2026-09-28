import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../core/services/api.service';
import { ServiceRequestAnalytics } from '../../../core/models/models';

@Component({
  selector: 'app-analytics',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './analytics.component.html',
  styleUrl: '../reports.css',
})
export class AnalyticsComponent implements OnInit {
  fromDate = '';
  toDate = '';
  category = '';
  status = '';

  data = signal<ServiceRequestAnalytics | null>(null);
  loading = signal(false);
  error = signal('');

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.run();
  }

  run() {
    this.loading.set(true);
    this.error.set('');
    this.api.serviceRequestAnalytics({
      from_date: this.fromDate || undefined,
      to_date: this.toDate || undefined,
      category: this.category || undefined,
      status: this.status || undefined,
    }).subscribe({
      next: (res) => {
        this.data.set(res);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Failed to load analytics.');
        this.loading.set(false);
      },
    });
  }

  maxCount(items: { count: number }[]): number {
    return Math.max(1, ...items.map((i) => i.count));
  }
}
