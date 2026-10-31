import { Component, OnInit, computed, inject, signal } from '@angular/core';

import {
  CategoriesClient, CategoryDto, MatchKind, PropertyDto, SearchClient, SearchMode, SearchResultDto, TextSearchClient,
  TextSearchResultDto, ValueDto,
} from './api/api-client';
import { environment } from '../environments/environment';
import { fillValue, problemMessage } from './fill-value';
import { ViewerDialog, ViewerTarget } from './viewer/viewer-dialog';

@Component({
  selector: 'app-root',
  imports: [ViewerDialog],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App implements OnInit {
  private readonly categoriesApi = inject(CategoriesClient);
  private readonly searchApi = inject(SearchClient);
  private readonly textApi = inject(TextSearchClient);

  protected readonly categories = signal<CategoryDto[]>([]);
  protected readonly properties = signal<PropertyDto[]>([]);
  protected readonly values = signal<ValueDto[]>([]);
  protected readonly results = signal<SearchResultDto[] | null>(null);

  protected readonly category = signal('');
  protected readonly property = signal('');
  protected readonly searchText = signal('');
  protected readonly mode = signal<SearchMode>(SearchMode.Near);
  protected readonly includeOld = signal(false);

  protected readonly loading = signal(false);
  protected readonly error = signal('');
  protected readonly viewing = signal<ViewerTarget | null>(null);

  // free-text search (M7)
  protected readonly view = signal<'filters' | 'text'>('filters');
  protected readonly tq = signal('');
  protected readonly tCategory = signal('');
  protected readonly tIncludeOld = signal(false);
  protected readonly tResults = signal<TextSearchResultDto[] | null>(null);
  protected readonly tLoading = signal(false);
  protected readonly kindLabel: Record<MatchKind, string> = {
    [MatchKind.PartNo]: 'Part no.', [MatchKind.BomLine]: 'BOM line', [MatchKind.Spec]: 'Spec value',
    [MatchKind.Note]: 'Note', [MatchKind.FileName]: 'File name',
  };
  /** Categories for the text-search scope: the filterable ones plus CAD (found by file name only). */
  protected readonly textCategories = computed(() => [...this.categories(), { key: 'cad', label: 'CAD files', docCount: 0 }]);

  protected readonly modes = [SearchMode.Near, SearchMode.Exact];
  protected readonly propertyInfo = computed(() => this.properties().find((p) => p.key === this.property()));
  protected readonly isNumeric = computed(() => this.propertyInfo()?.dataType === 'number');

  ngOnInit(): void {
    this.categoriesApi.getCategories().subscribe({
      next: (c) => {
        this.categories.set(c);
        if (c.length) this.selectCategory(c[0].key);   // demo convenience: start on the first category
      },
      error: (e) => this.error.set(`Cannot reach the API at ${environment.apiBaseUrl}. ${problemMessage(e)}`),
    });
  }

  /** Step 1. Changing it resets steps 2-4. */
  protected selectCategory(key: string): void {
    this.category.set(key);
    this.property.set('');
    this.properties.set([]);
    this.values.set([]);
    this.searchText.set('');
    this.results.set(null);
    this.error.set('');
    if (!key) return;
    this.categoriesApi.getProperties(key).subscribe({
      next: (p) => this.properties.set(p),
      error: (e) => this.error.set(problemMessage(e)),
    });
  }

  /** Step 2. Fills the step-3 value chips. */
  protected selectProperty(key: string): void {
    this.property.set(key);
    this.values.set([]);
    this.searchText.set('');
    this.results.set(null);
    this.error.set('');
    if (!key) return;
    this.categoriesApi.getValues(this.category(), key, undefined).subscribe({
      next: (v) => this.values.set(v),
      error: (e) => this.error.set(problemMessage(e)),
    });
  }

  /** Step 3: a chip fills the step-4 box. */
  protected pick(v: ValueDto): void {
    this.searchText.set(fillValue(v.display, this.propertyInfo()?.dataType ?? 'text'));
  }

  protected isPicked(v: ValueDto): boolean {
    return !!this.searchText() && this.searchText() === fillValue(v.display, this.propertyInfo()?.dataType ?? 'text');
  }

  /** Step 4. */
  protected go(): void {
    const value = this.searchText().trim();
    if (!this.category() || !this.property() || !value) return;
    this.loading.set(true);
    this.error.set('');
    this.searchApi.search(this.category(), this.property(), value, this.mode(), 20, this.includeOld()).subscribe({
      next: (r) => {
        this.results.set(r.results ?? []);
        this.loading.set(false);
      },
      error: (e) => {
        this.results.set(null);
        this.error.set(problemMessage(e));
        this.loading.set(false);
      },
    });
  }

  protected open(r: SearchResultDto): void {
    this.viewing.set({ documentId: r.documentId, fileName: r.fileName, page: r.page, bbox: r.bbox, matchedKey: this.property() });
  }

  protected fileUrl(id: number): string {
    return `${environment.apiBaseUrl}/api/documents/${id}/file`;
  }

  protected similarityPct(r: SearchResultDto): string {
    return r.similarity == null ? '' : `${Math.round(r.similarity * 100)}% similar`;
  }

  protected onInput(e: Event): void {
    this.searchText.set((e.target as HTMLInputElement).value);
  }

  protected onKey(e: KeyboardEvent): void {
    if (e.key === 'Enter') this.go();
  }

  // --- free-text search --------------------------------------------------------------------------

  protected setView(v: 'filters' | 'text'): void {
    this.view.set(v);
    this.error.set('');
  }

  protected goText(): void {
    const q = this.tq().trim();
    if (q.length < 3) {
      this.error.set('Type at least 3 characters.');
      return;
    }
    this.tLoading.set(true);
    this.error.set('');
    this.textApi.search(q, this.tCategory() || undefined, 20, this.tIncludeOld()).subscribe({
      next: (r) => {
        this.tResults.set(r.results);
        this.tLoading.set(false);
      },
      error: (e) => {
        this.tResults.set(null);
        this.error.set(problemMessage(e));
        this.tLoading.set(false);
      },
    });
  }

  protected openText(r: TextSearchResultDto): void {
    this.viewing.set({ documentId: r.documentId, fileName: r.fileName, page: r.page, bbox: r.bbox, matchedKey: r.matchedKey });
  }

  protected isPdf(r: { relPath: string }): boolean {
    return r.relPath.toLowerCase().endsWith('.pdf');
  }

  protected scorePct(r: TextSearchResultDto): string {
    return `${Math.round(r.score * 100)}%`;
  }

  protected onTextInput(e: Event): void {
    this.tq.set((e.target as HTMLInputElement).value);
  }

  protected onTextKey(e: KeyboardEvent): void {
    if (e.key === 'Enter') this.goText();
  }
}
