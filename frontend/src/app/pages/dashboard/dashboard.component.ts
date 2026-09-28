import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { Gate, GateAssignment } from '../../core/models/models';

interface AssignmentCard extends GateAssignment {
  colorClass: 'occupied' | 'upcoming' | 'buffer-risk' | 'idle';
  colorLabel: string;
}

interface GateColumn {
  gate: Gate;
  assignments: AssignmentCard[];
}

interface GateStat {
  gate_number: string;
  count: number;
  avgDurationMinutes: number;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css',
})
export class DashboardComponent implements OnInit {
  selectedDate = signal(this.today());
  gates = signal<Gate[]>([]);
  assignments = signal<GateAssignment[]>([]);
  loading = signal(false);
  error = signal('');

  constructor(private api: ApiService, public auth: AuthService) {}

  ngOnInit() {
    this.api.listGates().subscribe({ next: (g) => this.gates.set(g) });
    this.load();
  }

  today(): string {
    return new Date().toISOString().slice(0, 10);
  }

  onDateChange(value: string) {
    this.selectedDate.set(value);
    this.load();
  }

  load() {
    this.loading.set(true);
    this.error.set('');
    this.api.getGateAssignmentsByDate(this.selectedDate()).subscribe({
      next: (data) => {
        this.assignments.set(data);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Failed to load gate assignments for this date.');
        this.loading.set(false);
      },
    });
  }

  private classify(a: GateAssignment, gate: Gate, allForGate: GateAssignment[]): { colorClass: AssignmentCard['colorClass']; colorLabel: string } {
    if (gate.status !== 'operational') {
      return { colorClass: 'idle', colorLabel: 'Gray — gate unavailable' };
    }
    const now = Date.now();
    const start = new Date(a.start_time).getTime();
    const end = new Date(a.end_time).getTime();

    if (now >= start && now <= end) {
      return { colorClass: 'occupied', colorLabel: 'Green — currently occupied' };
    }

    const BUFFER_MS = 30 * 60 * 1000;
    const backToBack = allForGate.some((other) => {
      if (other.id === a.id) return false;
      const otherStart = new Date(other.start_time).getTime();
      const otherEnd = new Date(other.end_time).getTime();
      const gapBefore = start - otherEnd;
      const gapAfter = otherStart - end;
      return (gapBefore >= 0 && gapBefore <= BUFFER_MS) || (gapAfter >= 0 && gapAfter <= BUFFER_MS);
    });
    if (backToBack) {
      return { colorClass: 'buffer-risk', colorLabel: 'Red — back-to-back, minimum buffer' };
    }

    const TWO_HOURS_MS = 2 * 60 * 60 * 1000;
    if (start > now && start - now <= TWO_HOURS_MS) {
      return { colorClass: 'upcoming', colorLabel: 'Yellow — upcoming within 2 hours' };
    }

    return { colorClass: 'idle', colorLabel: 'Gray — scheduled, not imminent' };
  }

  gateColumns = computed<GateColumn[]>(() => {
    const gates = this.gates();
    const assignments = this.assignments();
    return gates.map((gate) => {
      const forGate = assignments.filter((a) => a.gate === gate.id);
      const cards: AssignmentCard[] = forGate
        .slice()
        .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())
        .map((a) => {
          const { colorClass, colorLabel } = this.classify(a, gate, forGate);
          return { ...a, colorClass, colorLabel };
        });
      return { gate, assignments: cards };
    });
  });

  utilisationStats = computed<{ gateStats: GateStat[]; mostUtilised: string; peakHour: string }>(() => {
    const assignments = this.assignments();
    const gates = this.gates();
    const byGate = new Map<number, GateAssignment[]>();
    for (const a of assignments) {
      const list = byGate.get(a.gate) ?? [];
      list.push(a);
      byGate.set(a.gate, list);
    }

    const gateStats: GateStat[] = gates.map((gate) => {
      const list = byGate.get(gate.id) ?? [];
      const totalMinutes = list.reduce((sum, a) => {
        return sum + (new Date(a.end_time).getTime() - new Date(a.start_time).getTime()) / 60000;
      }, 0);
      return {
        gate_number: gate.gate_number,
        count: list.length,
        avgDurationMinutes: list.length ? Math.round(totalMinutes / list.length) : 0,
      };
    });

    const mostUtilisedStat = gateStats.slice().sort((a, b) => b.count - a.count)[0];
    const mostUtilised = mostUtilisedStat && mostUtilisedStat.count > 0 ? `${mostUtilisedStat.gate_number} (${mostUtilisedStat.count} assignments)` : 'N/A';

    const hourCounts = new Array(24).fill(0);
    for (const a of assignments) {
      const hour = new Date(a.start_time).getUTCHours();
      hourCounts[hour]++;
    }
    let peakHourIdx = 0;
    let max = -1;
    hourCounts.forEach((c, i) => {
      if (c > max) {
        max = c;
        peakHourIdx = i;
      }
    });
    const peakHour = max > 0 ? `${String(peakHourIdx).padStart(2, '0')}:00 - ${String((peakHourIdx + 1) % 24).padStart(2, '0')}:00 UTC` : 'N/A';

    return { gateStats, mostUtilised, peakHour };
  });
}
