import React from "react";
import "./ProductIntroPanel.css";

const FEATURES = [
  { icon: "\u26a1", title: "AI \u7cbe\u5f69\u7247\u6bb5\u63a8\u8350", desc: "\u57fa\u4e8e\u7269\u4f53\u68c0\u6d4b\u3001\u573a\u666f\u5206\u6790\u3001\u8bed\u97f3\u8bc6\u522b\u548c\u8fd0\u52a8\u68c0\u6d4b\uff0c\u81ea\u52a8\u8bc6\u522b\u89c6\u9891\u4e2d\u7684\u7cbe\u5f69\u7247\u6bb5\u3002" },
  { icon: "\u2702\ufe0f", title: "Clip \u81ea\u52a8\u5bfc\u51fa", desc: "\u652f\u6301\u5c06\u63a8\u8350\u7684\u7cbe\u5f69\u7247\u6bb5\u5bfc\u51fa\u4e3a\u72ec\u7acb\u89c6\u9891\u6587\u4ef6\uff0c\u65b9\u4fbf\u4e0b\u8f7d\u548c\u5171\u4eab\u3002" },
  { icon: "\u23f1\ufe0f", title: "Timeline \u4ea4\u4e92", desc: "\u901a\u8fc7\u65f6\u95f4\u8f74\u53ef\u89c6\u5316\u67e5\u770b\u6240\u6709\u63a8\u8350\u7247\u6bb5\uff0c\u70b9\u51fb\u5373\u53ef\u8df3\u8f6c\u64ad\u653e\u3002" },
  { icon: "\ud83d\udcca", title: "\u53ef\u89e3\u91ca\u62a5\u544a", desc: "\u63d0\u4f9b\u8be6\u7ec6\u7684\u5206\u6790\u62a5\u544a\u548c\u6bcf\u4e2a\u7cbe\u5f69\u7247\u6bb5\u7684\u63a8\u8350\u539f\u56e0\u8bf4\u660e\u3002" },
];

export default function ProductIntroPanel() {
  return (
    <div className="product-intro">
      <h2 className="product-intro__heading">VideoMind Agent</h2>
      <p className="product-intro__sub">视频内容理解与自动剪辑工具</p>
      <div className="product-intro__grid">
        {FEATURES.map((f, i) => (
          <div key={i} className="product-intro__card">
            <span className="product-intro__icon">{f.icon}</span>
            <div>
              <h4 className="product-intro__card-title">{f.title}</h4>
              <p className="product-intro__card-desc">{f.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
