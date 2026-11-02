import { Container, Matrix, RenderTexture, Sprite } from 'pixi.js';

const W = 160, H = 200, FEET_X = W / 2, FEET_Y = H - 20, SCALE = 1.6, CENTER_X = 112, BOTTOM_Y = 228;

function mapAvatar($: any): Container | null {
  try {
    const sm = $.C('map.space.SpaceManager').instance;
    const army = sm?.model?.selfArmy;
    return army ? sm.controller?.getArmyView(army)?.avatarView ?? null : null;
  } catch {
    return null;
  }
}

function attach(view: any, $: any): void {
  const app = (globalThis as any).__app;
  if (view.__mirror || !app) return;
  const rt = RenderTexture.create({ width: W, height: H });
  const sprite = new Sprite(rt);
  sprite.scale.set(SCALE);
  sprite.x = CENTER_X - FEET_X * SCALE;
  sprite.y = BOTTOM_Y - FEET_Y * SCALE;
  Container.prototype.addChild.call(view, sprite);
  const transform = new Matrix();
  const tick = () => {
    const src = mapAvatar($);
    sprite.visible = !!src && !!view.parent;
    if (!sprite.visible) return;
    transform.set(1, 0, 0, 1, FEET_X - src!.x, FEET_Y - src!.y);
    app.renderer.render({ container: src!, target: rt, clear: true, transform });
  };
  app.ticker.add(tick);
  view.__mirror = () => { app.ticker.remove(tick); rt.destroy(true); };
}

export function mirrorMapAvatar(cls: any, $: any): void {
  const data = Object.getOwnPropertyDescriptor(cls.prototype, 'data')!;
  Object.defineProperty(cls.prototype, 'data', {
    ...data,
    set(v: unknown) { data.set!.call(this, v); attach(this, $); },
  });
  const dispose = cls.prototype.dispose;
  cls.prototype.dispose = function (this: any, ...args: unknown[]) {
    this.__mirror?.();
    this.__mirror = null;
    return dispose.apply(this, args);
  };
}
