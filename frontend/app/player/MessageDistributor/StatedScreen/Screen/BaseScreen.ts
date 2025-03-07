import styles from './screen.css';
import { getState } from '../../../store';

import type { Point } from './types';


export interface State {
  width: number;
  height: number;
}

export const INITIAL_STATE: State = {
  width: 0,
  height: 0,
}


export default abstract class BaseScreen {
  public    readonly overlay: HTMLDivElement;
  private   readonly iframe: HTMLIFrameElement;
  private   readonly _screen: HTMLDivElement;
  protected parentElement: HTMLElement | null = null;
  constructor() {
    const iframe = document.createElement('iframe');
    iframe.className = styles.iframe;
    this.iframe = iframe;

    const overlay = document.createElement('div');
    overlay.className = styles.overlay;
    this.overlay = overlay;

    const screen = document.createElement('div');

    setTimeout(function() {    
      iframe.contentDocument?.addEventListener('mousemove', function() {        
        overlay.style.display = 'block';
      })

      overlay.addEventListener('contextmenu', function() {
        overlay.style.display = 'none';
      })
    }, 10)

    screen.className = styles.screen;
    screen.appendChild(iframe);
    screen.appendChild(overlay);
    this._screen = screen;
  }

  attach(parentElement: HTMLElement) {
    if (this.parentElement) {
      throw new Error("BaseScreen: Trying to attach an attached screen.");
    }

    parentElement.appendChild(this._screen);

    this.parentElement = parentElement;
    // parentElement.onresize = this.scale;
    window.addEventListener('resize', this.scale);  
    this.scale();
  }

  get window(): WindowProxy | null {
    return this.iframe.contentWindow;
  }

  get document(): Document | null {
    return this.iframe.contentDocument;
  }

  private boundingRect: DOMRect | null  = null;
  private getBoundingClientRect(): DOMRect {
    //if (this.boundingRect === null) {
      return this.boundingRect = this.overlay.getBoundingClientRect(); // expensive operation?
    //}
    //return this.boundingRect;
  }

  getInternalCoordinates({ x, y }: Point): Point {
    const { x: overlayX, y: overlayY, width } = this.getBoundingClientRect();
    //console.log("x y ", x,y,'ovx y', overlayX, overlayY, width)

    const screenWidth = this.overlay.offsetWidth;

    const scale = screenWidth / width;
    const screenX = (x - overlayX) * scale;
    const screenY = (y - overlayY) * scale;

    return { x: screenX, y: screenY };
  }

  getElementFromInternalPoint({ x, y }: Point): Element | null {
    return this.document?.elementFromPoint(x, y) || null;
  }

  getElementsFromInternalPoint({ x, y }: Point): Element[] {
    // @ts-ignore (IE, Edge)
    if (typeof this.document?.msElementsFromRect === 'function') {
      // @ts-ignore
      return Array.prototype.slice.call(this.document?.msElementsFromRect(x,y)) || [];
    }

    if (typeof this.document?.elementsFromPoint === 'function') {
      return this.document?.elementsFromPoint(x, y) || [];     
    }
    const el = this.document?.elementFromPoint(x, y);
    return el ? [ el ] : [];
  }

  getElementFromPoint(point: Point): Element | null {
    return this.getElementFromInternalPoint(this.getInternalCoordinates(point));
  }

  getElementsFromPoint(point: Point): Element[] {
    return this.getElementsFromInternalPoint(this.getInternalCoordinates(point));
  }

  display(flag: boolean = true) {
    this._screen.style.display = flag ? '' : 'none';
  }

  displayFrame(flag: boolean = true) {
    this.iframe.style.display = flag ? '' : 'none';
  }

  _scale() {
    if (!this.parentElement) return;
    let s = 1;
    const { height, width } = getState();
    const { offsetWidth, offsetHeight } = this.parentElement;

    s = Math.min(offsetWidth / width, offsetHeight / height);
    if (s > 1) {
      s = 1;
    } else {
      s = Math.round(s * 1e3) / 1e3;
    }
    this._screen.style.transform =  `scale(${ s }) translate(-50%, -50%)`;
    this._screen.style.width = width + 'px';
    this._screen.style.height =  height + 'px';
    this.iframe.style.width = width + 'px';
    this.iframe.style.height = height + 'px';

    this.boundingRect = this.overlay.getBoundingClientRect();
  }

  scale = () => { // TODO: solve classes inheritance issues in typescript
    this._scale();
  }


  clean() {
    window.removeEventListener('resize', this.scale);
  }
}