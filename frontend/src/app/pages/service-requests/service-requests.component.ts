import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { ServiceRequest, ServiceRequestCategory, ServiceRequestStatus } from '../../core/models/models';

const CATEGORIES: ServiceRequestCategory[] = ['food', 'beverage', 'wheelchair', 'special_assistance', 'medical', 'lost_baggage', 'other'];

const VALID_TRANSITIONS: Record<ServiceRequestStatus, ServiceRequestStatus[]> = {
  open: ['in_progress', 'rejected'],
  in_progress: ['resolved', 'rejected'],
  resolved: [],
  rejected: [],
};

@Component({
  selector: 'app-service-requests',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './service-requests.component.html',
  styleUrl: './service-requests.component.css',
})
export class ServiceRequestsComponent implements OnInit {
  categories = CATEGORIES;
  requests = signal<ServiceRequest[]>([]);
  groundStaff = signal<{ id: number; username: string }[]>([]);
  loading = signal(false);
  error = signal('');

  // Passenger create-form state
  newFlightNo = '';
  newCategory: ServiceRequestCategory = 'food';
  newDetails = '';
  createError = signal('');
  createSuccess = signal(false);

  // Staff filters
  filterStatus = '';
  filterCategory = '';
  filterFlightNo = '';

  // Confirmation dialog state
  pendingAction = signal<{ request: ServiceRequest; newStatus: ServiceRequestStatus } | null>(null);
  resolutionNotesDraft = '';

  constructor(private api: ApiService, public auth: AuthService) {}

  ngOnInit() {
    this.load();
    if (this.auth.hasRole('admin', 'ground_staff')) {
      this.api.listGroundStaff().subscribe({ next: (s) => this.groundStaff.set(s) });
    }
  }

  isStaff(): boolean {
    return this.auth.hasRole('admin', 'ground_staff', 'gate_controller');
  }

  load() {
    this.loading.set(true);
    this.error.set('');
    const params = this.isStaff()
      ? {
          status: this.filterStatus || undefined,
          category: this.filterCategory || undefined,
          flight_no: this.filterFlightNo || undefined,
        }
      : undefined;
    this.api.listServiceRequests(params).subscribe({
      next: (data) => {
        this.requests.set(data);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Failed to load service requests.');
        this.loading.set(false);
      },
    });
  }

  createRequest() {
    this.createError.set('');
    this.createSuccess.set(false);
    if (!this.newFlightNo.trim()) {
      this.createError.set('Flight number is required.');
      return;
    }
    if (!this.newDetails.trim()) {
      this.createError.set('Please describe your request.');
      return;
    }
    this.api.createServiceRequest({
      flight_no: this.newFlightNo.trim().toUpperCase(),
      category: this.newCategory,
      details: this.newDetails.trim(),
    }).subscribe({
      next: () => {
        this.createSuccess.set(true);
        this.newFlightNo = '';
        this.newDetails = '';
        this.load();
      },
      error: (err) => {
        this.createError.set(err?.error?.message || 'Failed to create service request.');
      },
    });
  }

  validNextStatuses(current: ServiceRequestStatus): ServiceRequestStatus[] {
    return VALID_TRANSITIONS[current] ?? [];
  }

  requestStatusChange(request: ServiceRequest, newStatus: ServiceRequestStatus) {
    this.resolutionNotesDraft = '';
    this.pendingAction.set({ request, newStatus });
  }

  cancelAction() {
    this.pendingAction.set(null);
  }

  confirmAction() {
    const action = this.pendingAction();
    if (!action) return;
    const payload: { status: string; resolution_notes?: string } = { status: action.newStatus };
    if (action.newStatus === 'resolved' || action.newStatus === 'rejected') {
      payload.resolution_notes = this.resolutionNotesDraft;
    }
    this.api.updateServiceRequest(action.request.id, payload).subscribe({
      next: () => {
        this.pendingAction.set(null);
        this.load();
      },
      error: (err) => {
        this.error.set(err?.error?.message || 'Failed to update status.');
        this.pendingAction.set(null);
      },
    });
  }

  assignStaff(request: ServiceRequest, staffId: string) {
    if (!staffId) return;
    this.api.updateServiceRequest(request.id, { assigned_to: Number(staffId) }).subscribe({
      next: () => this.load(),
      error: (err) => this.error.set(err?.error?.message || 'Failed to assign staff.'),
    });
  }
}
