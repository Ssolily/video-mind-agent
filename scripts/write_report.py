content = r"""# P1-A3 Step 5: VideoPlayer 组件与区间播放控制 Hook

## 一、修改和新增文件列表

| 文件 | 状态 | 说明 |
|------|------|------|
| frontend/src/types/playback.ts | **新增** | 播放器相关类型定义 |
| frontend/src/hooks/useVideoPlayback.ts | **新增** | 播放控制 Hook |
| frontend/src/hooks/useVideoPlayback.test.tsx | **新增** | Hook 测试 |
| frontend/src/components/VideoPlayer.tsx | **新增** | 视频播放器组件 |
| frontend/src/components/VideoPlayer.test.tsx | **新增** | 组件测试 |
| frontend/src/App.tsx | **未修改** | 未接入主流程 |

## 二、VideoPlayer Props

| Prop | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| src | string \| null | -- | 视频源 URL（支持相对 API URL 和 HTTP URL） |
| segment | PlaybackSegment \| null \| undefined | -- | 播放区间，设置后自动跳到 startTime 播放到 endTime |
| seekRequest | SeekRequest \| null \| undefined | -- | 跳转请求，requestId 变化时触发 seek |
| segmentEndTolerance | number | 0.1 | 区间结束检测容差（秒） |
| className | string \| undefined | -- | 外层 div 类名 |
| ariaLabel | string \| undefined | \u89c6\u9891\u64ad\u653e\u5668 | accessibility label |
| onTimeUpdate | (currentTime: number) => void | -- | timeupdate 回调 |
| onDurationChange | (duration: number) => void | -- | duration 变化回调 |
| onPlayingChange | (playing: boolean) => void | -- | 播放/暂停状态变化回调 |
| onSegmentEnd | (segment: PlaybackSegment) => void | -- | 区间播放结束回调 |
| onError | (message: string) => void | -- | 媒体错误回调 |

## 三、forwardRef 与 VideoPlayerHandle

**是否使用 forwardRef:** 是

**VideoPlayerHandle 接口:**

```typescript
interface VideoPlayerHandle {
  play: () => Promise<boolean>;
  pause: () => void;
  seek: (time: number, autoplay?: boolean) => Promise<boolean>;
  playSegment: (segment: PlaybackSegment) => Promise<boolean>;
  clearSegment: () => void;
  getCurrentTime: () => number;
  getDuration: () => number;
  getPlaying: () => boolean;
}
```

## 四、useVideoPlayback 输入和输出

**输入 (UseVideoPlaybackOptions):**

```typescript
interface UseVideoPlaybackOptions {
  src: string | null;
  segment?: PlaybackSegment | null;
  seekRequest?: SeekRequest | null;
  segmentEndTolerance?: number;
  onTimeUpdate?: (currentTime: number) => void;
  onDurationChange?: (duration: number) => void;
  onPlayingChange?: (playing: boolean) => void;
  onSegmentEnd?: (segment: PlaybackSegment) => void;
  onError?: (message: string) => void;
}
```

**输出 (UseVideoPlaybackReturn):**

```typescript
interface UseVideoPlaybackReturn {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  currentTime: number;
  duration: number;
  playing: boolean;
  mediaError: string | null;
  play: () => Promise<boolean>;
  pause: () => void;
  seek: (time: number, autoplay?: boolean) => Promise<boolean>;
  playSegment: (segment: PlaybackSegment) => Promise<boolean>;
  clearSegment: () => void;
}
```

## 五、时间规范化规则

- normalizeTime(t): Number.isFinite(t) && t >= 0 ? t : 0
- 所有时间以秒为单位
- startTime 和 endTime 不在类型层自动调换

## 六、Segment 规范化规则

- Hook 内部从 props 同步到 segmentRef.current（useEffect + useRef）
- 设置新 segment 时重置 segmentEndFiredRef.current = false
- segment 变化时自动 el.currentTime = startTime + el.play()
- clearSegment() 仅清除 ref 状态，不修改 video element

## 七、seekRequest 和 requestId 行为

- seekRequestRef 保存已处理的最后一个请求
- 相同 requestId 不会重复 seek
- 不同 requestId 触发 el.currentTime = time + 可选 autoplay
- 无效 requestId（NaN、非数字）静默忽略

## 八、play Promise rejection 处理

- 所有 el.play() 调用使用 .catch(() => {}) 或 try/catch
- play() 和 playSegment() 返回 Promise<boolean>，被拒绝时返回 false
- 不会产生未处理的 promise rejection

## 九、区间结束检测方式

- 通过 timeupdate 事件
- 当 currentTime >= endTime - tolerance 时触发
- 使用 segmentEndFiredRef 防止重复触发

## 十、onSegmentEnd 防重复机制

- segmentEndFiredRef boolean ref，首次触发 end 后设为 true
- 后续 timeupdate 不会重复调用
- segment prop 变化时才重置

## 十一、clearSegment 行为

- segmentRef.current = null
- segmentEndFiredRef.current = false
- 不会暂停正在播放的视频

## 十二、src 改变时清理内容

- 重置所有 React state
- 重置所有 ref

## 十三、媒体错误映射

MEDIA_ERROR_MESSAGES:
- code 1: \u89c6\u9891\u52a0\u8f7d\u88ab\u7528\u6237\u6216\u6d4f\u89c8\u5668\u4e2d\u65ad
- code 2: \u89c6\u9891\u683c\u5f0f\u4e0d\u652f\u6301\u6216\u7f51\u7edc\u9519\u8bef
- code 3: \u89c6\u9891\u89e3\u7801\u5931\u8d25\uff0c\u7f16\u7801\u683c\u5f0f\u4e0d\u53d7\u652f\u6301
- code 4: \u89c6\u9891\u8d44\u6e90\u4e0d\u53ef\u7528\u6216\u683c\u5f0f\u4e0d\u652f\u6301

## 十四、是否使用 requestAnimationFrame

否。timeupdate 使用原生 HTML5 事件。

## 十五、测试统计

**Hook 测试:** 18 tests
**VideoPlayer 测试:** 22 tests
**原有测试:** 39 tests
**共:** 75 passed, 0 failed, 0 skipped

## 十六、验证结果

| 命令 | 结果 |
|------|------|
| npm run typecheck | 0 errors |
| npm run test:run | 75 passed, 0 failed |
| npm run build | success |
| backend pytest -ra -q | 240 passed, 0 failed |

## 十七、关键问题回答

| 问题 | 答案 |
|------|------|
| \u662f\u5426\u4f7f\u7528\u539f\u751f <video> | \u662f |
| \u662f\u5426 fetch \u89c6\u9891\u4e8c\u8fdb\u5236 | \u5426 |
| \u662f\u5426\u521b\u5efa Blob URL | \u5426 |
| \u662f\u5426\u652f\u6301 Range \u63a5\u53e3 URL | \u662f |
| \u662f\u5426\u53ef\u4ee5\u91cd\u590d\u64ad\u653e\u540c\u4e00\u4e2a Highlight | \u662f |
| \u662f\u5426\u53ef\u4ee5\u5728\u533a\u95f4\u7ed3\u675f\u65f6\u81ea\u52a8\u6682\u505c | \u662f |
| play() \u88ab\u6d4f\u89c8\u5668\u62d2\u7edd\u65f6\u662f\u5426\u5b89\u5168 | \u662f |
| src \u6539\u53d8\u540e\u65e7\u533a\u95f4\u662f\u5426\u4f1a\u6b8b\u7559 | \u5426 |
| clearSegment \u540e\u662f\u5426\u53ef\u4ee5\u5b8c\u6574\u64ad\u653e | \u662f |
| \u662f\u5426\u5b9e\u73b0\u4e86 Timeline | \u5426 |
| \u662f\u5426\u4fee\u6539\u4e86\u540e\u7aef | \u5426 |

## 十八、已知限制

1. \u65e0 pending seek \u961f\u5217
2. \u672a\u63a5\u5165 App.tsx
3. \u65e0\u7f13\u51b2\u8fdb\u5ea6\u6761
4. \u65e0\u952e\u76d8\u5feb\u6377\u952e
"""

import sys
with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(content)
print('Report written')
