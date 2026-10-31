import { Component, OnInit, inject, input, output, signal } from '@angular/core';
import { NgxExtendedPdfViewerModule, PageRenderedEvent } from 'ngx-extended-pdf-viewer';

import { DocumentDetailDto, DocumentsClient, SpecDto } from '../api/api-client';
import { environment } from '../../environments/environment';

/** What to open: the document, and optionally the page + bbox of the matched value to highlight. */
export interface ViewerTarget {
  documentId: number;
  fileName: string;
  page?: number;
  bbox?: number[];
  matchedKey?: string;
}

type PageView = PageRenderedEvent['source'];

@Component({
  selector: 'app-viewer-dialog',
  imports: [NgxExtendedPdfViewerModule],
  templateUrl: './viewer-dialog.html',
  styleUrl: './viewer-dialog.css',
})
export class ViewerDialog implements OnInit {
  private readonly documents = inject(DocumentsClient);

  readonly target = input.required<ViewerTarget>();
  readonly closed = output<void>();

  protected readonly detail = signal<DocumentDetailDto | null>(null);
  protected readonly docId = signal(0);
  protected readonly pageNo = signal<number | undefined>(1);
  protected readonly highlight = signal<{ page: number; bbox: number[]; key?: string } | null>(null);
  protected readonly error = signal('');
  // 100% keeps A0/A1 spec-box text legible (and under pdf.js's canvas size limit); whole-page view when nothing to show
  protected readonly zoom = signal<number | string>('page-width');

  private readonly views = new Map<number, PageView>();
  private scrollUntil = 0;

  protected get pdfUrl(): string {
    return `${environment.apiBaseUrl}/api/documents/${this.docId()}/file`;
  }

  protected fileUrl(id: number): string {
    return `${environment.apiBaseUrl}/api/documents/${id}/file`;
  }

  ngOnInit(): void {
    const t = this.target();
    this.open(t.documentId, t.page, t.bbox, t.matchedKey);
  }

  protected open(id: number, page?: number, bbox?: number[], key?: string): void {
    this.views.clear();
    this.detail.set(null);
    this.error.set('');
    this.docId.set(id);
    this.pageNo.set(page ?? 1);
    if (bbox) this.requestScroll();
    this.zoom.set(bbox ? 100 : 'page-width');
    this.highlight.set(page && bbox ? { page, bbox, key } : null);
    this.documents.get(id).subscribe({
      next: (d) => this.detail.set(d),
      error: () => this.error.set('Could not load document details.'),
    });
  }

  /** Jump to an extracted value from the side panel. */
  protected focus(s: SpecDto): void {
    if (!s.page || !s.bbox) return;
    this.highlight.set({ page: s.page, bbox: s.bbox, key: s.key });
    this.requestScroll();
    if (this.pageNo() !== s.page) this.pageNo.set(s.page);
    else this.paint(s.page);
  }

  protected onPageRendered(e: PageRenderedEvent): void {
    this.views.set(e.pageNumber, e.source);
    this.paint(e.pageNumber);
  }

  /**
   * The bbox is in PDF points, top-left origin, in the displayed orientation (scope.md §4/§9).
   * pdf.js already applies /Rotate, so overlay = bbox x viewport.scale with no further transform.
   */
  private paint(pageNumber: number): void {
    const view = this.views.get(pageNumber);
    const h = this.highlight();
    if (!view || !h || h.page !== pageNumber) return;
    view.div.querySelectorAll('.ds-highlight').forEach((n) => n.remove());
    const k = view.viewport.scale;
    const [x0, y0, x1, y1] = h.bbox;
    const pad = 4;
    const el = document.createElement('div');
    el.className = 'ds-highlight';
    el.style.left = `${x0 * k - pad}px`;
    el.style.top = `${y0 * k - pad}px`;
    el.style.width = `${(x1 - x0) * k + pad * 2}px`;
    el.style.height = `${(y1 - y0) * k + pad * 2}px`;
    view.div.appendChild(el);
    // pdf.js re-renders (and resets the scroll) when the zoom is applied after load, so keep bringing the
    // highlight into view for a short window instead of only on the first render.
    if (Date.now() < this.scrollUntil) {
      setTimeout(() => el.scrollIntoView({ block: 'center', inline: 'center' }), 60);
    }
  }

  private requestScroll(): void {
    this.scrollUntil = Date.now() + 3000;
  }

  protected isMatch(s: SpecDto): boolean {
    return s.key === this.highlight()?.key;
  }
}
