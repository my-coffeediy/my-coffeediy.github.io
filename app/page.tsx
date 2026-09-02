"use client";

import { useMemo, useState, type CSSProperties } from "react";
import {
  ArrowUpRight,
  Check,
  ChevronRight,
  Clock3,
  Coffee,
  Droplets,
  Search,
  Shuffle,
  Snowflake,
  Sparkles,
  ThermometerSun,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type Category = "招牌系列" | "风味拿铁" | "创意美式" | "经典咖啡";

type Drink = {
  id: string;
  name: string;
  english: string;
  category: Category;
  availability: "当季上新" | "热门回归" | "热门常驻" | "经典常驻" | "门店为准";
  temperature: "冰" | "冰 / 热" | "热";
  time: string;
  difficulty: "超简单" | "简单" | "稍讲究";
  flavor: string;
  note: string;
  color: string;
  tint: string;
  ingredients: string[];
  steps: string[];
  tips: string[];
};

const drinks: Drink[] = [
  {
    id: "coconut-latte",
    name: "生椰拿铁",
    english: "Coconut Latte",
    category: "招牌系列",
    availability: "热门常驻",
    temperature: "冰 / 热",
    time: "5 分钟",
    difficulty: "超简单",
    flavor: "椰香 · 顺滑 · 清爽",
    note: "第一次复刻就选它，容错率最高。",
    color: "#2267ea",
    tint: "#eaf2ff",
    ingredients: ["双份浓缩咖啡 36ml", "厚椰乳 200ml", "冰块 120–140g", "糖浆 0–5ml（可不加）"],
    steps: ["杯中装满约七分冰块。", "倒入厚椰乳；嗜甜可先混入少量糖浆。", "沿冰块缓慢淋入浓缩咖啡，喝前搅匀。"],
    tips: ["没有咖啡机：3g 冻干咖啡＋30ml 热水。", "热饮不要把椰乳煮沸，加热到约 60℃ 即可。"],
  },
  {
    id: "butter-latte",
    name: "小黄油拿铁",
    english: "Butter Latte",
    category: "招牌系列",
    availability: "热门常驻",
    temperature: "冰 / 热",
    time: "7 分钟",
    difficulty: "简单",
    flavor: "黄油饼干香 · 奶甜",
    note: "像一块泡进咖啡里的黄油曲奇。",
    color: "#e9a81a",
    tint: "#fff5d9",
    ingredients: ["双份浓缩咖啡 36ml", "牛奶 170ml", "淡奶油 25ml", "焦糖糖浆 8ml", "食用黄油香草风味液 1滴（可选）", "冰块 120g"],
    steps: ["将牛奶、淡奶油、焦糖糖浆混匀。", "杯中加冰，倒入调好的黄油风味奶。", "最后淋入浓缩咖啡，充分搅匀。"],
    tips: ["不要直接放一大块黄油，容易油水分离。", "仅使用食品级风味液；没有就用焦糖糖浆，也很好喝。"],
  },
  {
    id: "butter-americano",
    name: "小黄油美式",
    english: "Butter Americano",
    category: "招牌系列",
    availability: "热门常驻",
    temperature: "冰 / 热",
    time: "5 分钟",
    difficulty: "简单",
    flavor: "烘焙奶香 · 清爽回甘",
    note: "闻起来甜，喝起来仍是轻盈美式。",
    color: "#cb8621",
    tint: "#fff3df",
    ingredients: ["双份浓缩咖啡 36ml", "纯净水 150ml", "焦糖糖浆 8ml", "淡奶油 15ml", "食用黄油香草风味液 1滴（可选）", "冰块 130g"],
    steps: ["焦糖糖浆与浓缩咖啡混合。", "杯中加满冰和水，倒入咖啡。", "淡奶油稍微打至流动状态，薄薄淋在表面。"],
    tips: ["想做“全冰去水”，把水省略、冰加满，边融边喝。", "黄油感来自烘焙风味，不建议直接加固体黄油。"],
  },
  {
    id: "orange-americano",
    name: "橙C美式",
    english: "Orange Americano",
    category: "创意美式",
    availability: "热门常驻",
    temperature: "冰",
    time: "4 分钟",
    difficulty: "超简单",
    flavor: "鲜橙 · 酸甜 · 解腻",
    note: "像橙汁里长出一层咖啡香。",
    color: "#ff7a1a",
    tint: "#fff0e4",
    ingredients: ["NFC 橙汁 180ml", "双份浓缩咖啡 36ml", "冰块 130g", "糖浆 0–8ml（按橙汁酸度）"],
    steps: ["杯中加冰，倒入 NFC 橙汁。", "橙汁偏酸时加入少量糖浆搅匀。", "沿冰块缓慢倒入冷却后的浓缩咖啡。"],
    tips: ["咖啡先放凉，果香更干净。", "不建议加牛奶，柑橘酸可能让牛奶结块。"],
  },
  {
    id: "fresh-lemon-americano",
    name: "鲜切柠C美式",
    english: "Fresh Lemon Americano",
    category: "创意美式",
    availability: "当季上新",
    temperature: "冰",
    time: "8 分钟",
    difficulty: "简单",
    flavor: "鲜柠 · 酸爽 · 咖啡感",
    note: "2026 夏季公开新品，适合闷热下午。",
    color: "#bdd326",
    tint: "#f5f9dc",
    ingredients: ["香水柠檬 1/2个", "柠檬汁 20ml", "双份浓缩咖啡 36ml", "纯净水 110ml", "糖浆 10–15ml", "冰块 140g"],
    steps: ["柠檬切片，去籽后与糖浆在杯底轻轻捶打出香。", "加入柠檬汁、冰块和纯净水。", "最后淋入放凉的浓缩咖啡，搅匀饮用。"],
    tips: ["捶打表皮 4–6 下即可，过度会发苦。", "胃酸敏感时减少柠檬汁，空腹不建议喝。"],
  },
  {
    id: "lemon-sparkling-americano",
    name: "柠C气泡美式",
    english: "Lemon Sparkling Americano",
    category: "创意美式",
    availability: "当季上新",
    temperature: "冰",
    time: "6 分钟",
    difficulty: "简单",
    flavor: "气泡 · 鲜柠 · 轻苦",
    note: "有气泡的柠檬咖啡，醒神感更强。",
    color: "#87c93b",
    tint: "#edf9df",
    ingredients: ["香水柠檬 1/3个", "柠檬汁 18ml", "无糖气泡水 160ml", "浓缩咖啡 30ml", "糖浆 10ml", "冰块 140g"],
    steps: ["杯底轻捶柠檬片和糖浆。", "加满冰，沿杯壁缓慢倒入气泡水。", "最后轻轻淋入冷却的浓缩咖啡，只搅两下。"],
    tips: ["气泡水和咖啡都要冷，才不容易喷溢。", "咖啡要最后加，层次和气泡感更好。"],
  },
  {
    id: "lacto-americano",
    name: "乳酸菌美式",
    english: "Lacto Americano",
    category: "创意美式",
    availability: "当季上新",
    temperature: "冰",
    time: "4 分钟",
    difficulty: "超简单",
    flavor: "乳酸酸甜 · 咖啡微苦",
    note: "2026 夏季回归款，家庭版不需要专用吸管。",
    color: "#54b8ed",
    tint: "#e7f7ff",
    ingredients: ["乳酸菌饮料 100ml", "无糖气泡水 80ml", "浓缩咖啡 30ml", "冰块 140g"],
    steps: ["乳酸菌饮料与气泡水都提前冷藏。", "杯中装满冰，先倒乳酸菌饮料，再加气泡水。", "沿冰块淋入冷却的浓缩咖啡，轻轻搅匀。"],
    tips: ["所有液体保持低温，能减少分层和絮凝。", "成品立即喝，不建议久放或加热。"],
  },
  {
    id: "velvet-latte",
    name: "丝绒拿铁",
    english: "Velvet Latte",
    category: "风味拿铁",
    availability: "热门常驻",
    temperature: "冰 / 热",
    time: "7 分钟",
    difficulty: "简单",
    flavor: "绵密 · 奶香 · 低苦",
    note: "重点不是甜，而是入口柔软。",
    color: "#c77f68",
    tint: "#faeee9",
    ingredients: ["双份浓缩咖啡 36ml", "牛奶 165ml", "淡奶油 25ml", "炼乳 6–8g", "冰块 120g"],
    steps: ["牛奶、淡奶油与炼乳充分混匀。", "冰饮加冰后倒入丝绒奶；热饮加热至约 60℃。", "加入浓缩咖啡，搅匀即可。"],
    tips: ["淡奶油只占一小部分，放多会腻。", "减糖版把炼乳减到 3g，奶感仍然足。"],
  },
  {
    id: "thick-milk-latte",
    name: "厚乳拿铁",
    english: "Thick Milk Latte",
    category: "风味拿铁",
    availability: "热门常驻",
    temperature: "冰 / 热",
    time: "6 分钟",
    difficulty: "超简单",
    flavor: "厚奶 · 醇香 · 饱满",
    note: "比普通拿铁更浓，但不必堆很多糖。",
    color: "#b98261",
    tint: "#f7eee8",
    ingredients: ["双份浓缩咖啡 36ml", "牛奶 150ml", "淡奶油 30ml", "炼乳 5g", "冰块 120g"],
    steps: ["牛奶、淡奶油和炼乳搅至完全融合。", "杯中加冰，倒入厚乳基底。", "淋入浓缩咖啡，搅匀。"],
    tips: ["想轻盈些：淡奶油减至 15ml，牛奶补足。", "热饮只加热不煮沸，奶香更干净。"],
  },
  {
    id: "mascarpone-latte",
    name: "马斯卡彭生酪拿铁",
    english: "Mascarpone Latte",
    category: "风味拿铁",
    availability: "门店为准",
    temperature: "冰 / 热",
    time: "10 分钟",
    difficulty: "稍讲究",
    flavor: "芝士 · 咸香 · 奶油感",
    note: "像一杯可以喝的轻盈提拉米苏。",
    color: "#d5a55a",
    tint: "#fff5e4",
    ingredients: ["马斯卡彭奶酪 20g", "牛奶 165ml", "淡奶油 15ml", "浓缩咖啡 36ml", "糖浆 5ml", "冰块 100g"],
    steps: ["取 40ml 温牛奶，与马斯卡彭搅到无颗粒。", "加入剩余牛奶、淡奶油和糖浆混匀。", "冰饮加冰后倒入奶酪乳，再淋咖啡；热饮整体加热后加咖啡。"],
    tips: ["马斯卡彭先回温 10 分钟，更容易搅匀。", "奶酪本身有厚度，糖浆少放更耐喝。"],
  },
  {
    id: "jasmine-latte",
    name: "茉莉花香拿铁",
    english: "Jasmine Latte",
    category: "风味拿铁",
    availability: "门店为准",
    temperature: "冰",
    time: "10 分钟",
    difficulty: "简单",
    flavor: "茉莉花香 · 奶咖",
    note: "茶和咖啡都在，但谁也不抢谁。",
    color: "#5dbf9a",
    tint: "#e6f7f0",
    ingredients: ["茉莉花茶 5g", "热水 110ml", "牛奶 115ml", "浓缩咖啡 30ml", "冰块 120g", "糖浆 0–5ml"],
    steps: ["茉莉花茶用 85℃ 热水浸泡 5 分钟，滤出并放凉。", "杯中加冰，倒入茶汤、牛奶和可选糖浆。", "最后淋入浓缩咖啡，搅匀。"],
    tips: ["不要用沸水久泡，茶汤发涩会压住花香。", "选清爽型牛奶，比厚乳更显茶香。"],
  },
  {
    id: "meteorite-latte",
    name: "陨石拿铁",
    english: "Meteorite Latte",
    category: "风味拿铁",
    availability: "门店为准",
    temperature: "冰",
    time: "8 分钟",
    difficulty: "简单",
    flavor: "黑糖 · Q弹 · 奶咖",
    note: "喝得到的“陨石”，是黑糖晶球或寒天。",
    color: "#654637",
    tint: "#f0e9e5",
    ingredients: ["黑糖寒天晶球 40g", "黑糖浆 12ml", "牛奶 170ml", "浓缩咖啡 36ml", "冰块 100g"],
    steps: ["杯壁淋一圈黑糖浆，杯底放入寒天晶球。", "加入冰块和牛奶。", "最后倒入浓缩咖啡，喝时用粗吸管搅匀。"],
    tips: ["寒天晶球比珍珠省去现煮步骤。", "黑糖浆已有甜度，不必再加糖。"],
  },
  {
    id: "coconut-americano",
    name: "生椰美式",
    english: "Coconut Americano",
    category: "创意美式",
    availability: "门店为准",
    temperature: "冰",
    time: "4 分钟",
    difficulty: "超简单",
    flavor: "椰子水 · 轻盈 · 咖啡",
    note: "比生椰拿铁更轻、更适合大口喝。",
    color: "#3f9bc4",
    tint: "#e5f5fb",
    ingredients: ["椰子水 160ml", "厚椰乳 30ml", "浓缩咖啡 36ml", "冰块 140g"],
    steps: ["椰子水与厚椰乳搅匀。", "杯中加满冰，倒入椰子基底。", "淋入冷却后的浓缩咖啡。"],
    tips: ["用无额外加糖的椰子水，口感更清爽。", "厚椰乳只放一点，用来增加香气而非厚重感。"],
  },
  {
    id: "grapefruit-americano",
    name: "柚C美式",
    english: "Grapefruit Americano",
    category: "创意美式",
    availability: "门店为准",
    temperature: "冰",
    time: "5 分钟",
    difficulty: "超简单",
    flavor: "西柚 · 微苦 · 酸甜",
    note: "果汁的苦与咖啡的苦，意外合拍。",
    color: "#f06c75",
    tint: "#fff0f1",
    ingredients: ["NFC 西柚汁 160ml", "纯净水 30ml", "浓缩咖啡 36ml", "糖浆 0–8ml", "冰块 130g"],
    steps: ["杯中加冰，倒入西柚汁与水。", "尝一下酸度，按需加入少量糖浆。", "最后淋入冷却浓缩咖啡。"],
    tips: ["选不含果肉膜的果汁，苦味更干净。", "正在服用会与西柚相互作用的药物时不要饮用。"],
  },
  {
    id: "classic-latte",
    name: "拿铁",
    english: "Caffè Latte",
    category: "经典咖啡",
    availability: "经典常驻",
    temperature: "冰 / 热",
    time: "5 分钟",
    difficulty: "超简单",
    flavor: "奶香 · 平衡 · 日常",
    note: "最基础，也最能看出咖啡和牛奶是否顺口。",
    color: "#8c644c",
    tint: "#f3ece7",
    ingredients: ["双份浓缩咖啡 36ml", "牛奶 190ml", "冰块 120g（冰饮）"],
    steps: ["冰饮：杯中加冰和牛奶，再倒浓缩。", "热饮：牛奶加热至 60–65℃，打出薄奶泡。", "将牛奶倒入浓缩咖啡，轻轻融合。"],
    tips: ["牛奶不要煮沸，否则甜感和顺滑度都会下降。", "没有奶泡机，用密封瓶摇奶后再微波加热也可以。"],
  },
  {
    id: "americano",
    name: "标准美式",
    english: "Americano",
    category: "经典咖啡",
    availability: "经典常驻",
    temperature: "冰 / 热",
    time: "3 分钟",
    difficulty: "超简单",
    flavor: "纯粹 · 清爽 · 烘焙香",
    note: "今天只想醒一醒，就不要加戏。",
    color: "#3e332f",
    tint: "#ece9e7",
    ingredients: ["双份浓缩咖啡 36ml", "纯净水 160ml", "冰块 140g（冰饮）"],
    steps: ["冰美式：杯中加冰和水，再倒浓缩。", "热美式：先加 80–85℃ 热水，再加浓缩。", "轻轻搅匀，按个人口味调整水量。"],
    tips: ["水少更浓，水多更清爽，没有唯一正确比例。", "冰饮先水后咖啡，香气和分层都更好。"],
  },
  {
    id: "thai-coffee-latte",
    name: "泰奶鸳鸯拿铁",
    english: "Thai Tea Coffee Latte",
    category: "风味拿铁",
    availability: "当季上新",
    temperature: "冰",
    time: "12 分钟",
    difficulty: "稍讲究",
    flavor: "泰式红茶 · 奶酪香 · 咖啡",
    note: "截图里的新款：泰奶与浓缩咖啡双重醇香。",
    color: "#d98228",
    tint: "#fff0dc",
    ingredients: ["泰式红茶 8g", "95℃ 热水 120ml", "牛奶 90ml", "淡奶 25ml", "炼乳 10g", "浓缩咖啡 30ml", "冰块 120g"],
    steps: ["泰式红茶用热水浸泡 6 分钟，滤出约 90ml 浓茶汤。", "趁温热加入炼乳和淡奶搅匀，放凉后加入牛奶。", "杯中加冰，倒入泰奶基底，最后缓慢淋入浓缩咖啡。"],
    tips: ["没有泰式红茶，可用锡兰红茶加 1 滴香草精替代。", "不额外加糖仍会有炼乳甜度，先按 10g 试做。"],
  },
  {
    id: "apple-c-americano",
    name: "苹果C美式",
    english: "Apple C Americano",
    category: "创意美式",
    availability: "热门回归",
    temperature: "冰",
    time: "4 分钟",
    difficulty: "超简单",
    flavor: "冰糖心苹果 · 清甜 · 咖啡",
    note: "阿克苏苹果汁路线，清爽度和橙C美式相近。",
    color: "#f05f69",
    tint: "#fff0f2",
    ingredients: ["NFC 苹果汁 200ml", "双份浓缩咖啡 36–38ml", "冰块 120–140g", "柠檬汁 2ml（可选）"],
    steps: ["苹果汁与咖啡提前冷却。", "杯中装满约七分冰块，倒入苹果汁。", "沿冰块缓慢淋入浓缩咖啡；想更清亮可加 2ml 柠檬汁。"],
    tips: ["选配料表只有苹果汁的 NFC 产品。", "苹果汁本身够甜，通常不需要另加糖。"],
  },
  {
    id: "aksu-apple-latte",
    name: "阿克苏苹果拿铁",
    english: "Aksu Apple Latte",
    category: "风味拿铁",
    availability: "门店为准",
    temperature: "冰",
    time: "6 分钟",
    difficulty: "简单",
    flavor: "苹果清甜 · 厚乳 · 咖啡",
    note: "苹果果香更明显，入口像一杯清甜奶咖。",
    color: "#df779a",
    tint: "#fdeef4",
    ingredients: ["阿克苏苹果汁 100ml", "牛奶 50ml", "厚乳 50ml", "浓缩咖啡 30ml", "冰块 100–120g"],
    steps: ["苹果汁、牛奶和厚乳全部提前冷藏。", "杯中加冰，先倒苹果汁，再沿杯壁慢慢加入牛奶与厚乳。", "最后淋入冷却浓缩咖啡，轻搅后立即饮用。"],
    tips: ["果汁遇奶可能有轻微絮凝，低温、慢倒并现做现喝。", "介意絮凝时用 15ml 苹果糖浆＋85ml 冷水替代果汁。"],
  },
  {
    id: "osmanthus-rice-latte",
    name: "桂花米酿拿铁",
    english: "Osmanthus Rice Latte",
    category: "风味拿铁",
    availability: "当季上新",
    temperature: "冰",
    time: "10 分钟",
    difficulty: "稍讲究",
    flavor: "桂花 · 米酿 · 乌龙 · 咖啡",
    note: "2026 秋季风味，甜润米香后面带一点乌龙。",
    color: "#c99a4f",
    tint: "#fff5e2",
    ingredients: ["无酒精甜米酿汁 40ml", "浓乌龙茶汤 60ml", "牛奶 110ml", "浓缩咖啡 30ml", "桂花糖浆 6–8ml", "冰块 110g"],
    steps: ["乌龙茶泡浓后滤出 60ml，彻底放凉。", "甜米酿汁、乌龙茶汤、牛奶和桂花糖浆混匀。", "杯中加冰，倒入米酿奶基底，再淋入浓缩咖啡。"],
    tips: ["选可直接饮用的无酒精甜米酿汁，风味更稳定。", "桂花糖浆宁少勿多，过量会遮住咖啡香。"],
  },
  {
    id: "sea-salt-caramel-latte",
    name: "海盐焦糖拿铁",
    english: "Sea Salt Caramel Latte",
    category: "风味拿铁",
    availability: "门店为准",
    temperature: "冰 / 热",
    time: "8 分钟",
    difficulty: "简单",
    flavor: "焦糖甜香 · 海盐回味 · 奶咖",
    note: "咸甜平衡，焦糖味会让咖啡更圆润。",
    color: "#b8793c",
    tint: "#fbefe2",
    ingredients: ["双份浓缩咖啡 36ml", "牛奶 170ml", "淡奶油 20ml", "焦糖酱 12g", "海盐 0.2g", "冰块 110g（冰饮）"],
    steps: ["焦糖酱加入浓缩咖啡搅匀。", "淡奶油与海盐轻轻打至仍可流动。", "冰杯加入冰和牛奶，倒入焦糖咖啡，最后淋上海盐奶油。"],
    tips: ["海盐只要一小撮，约 0.2g，放多会发苦。", "热饮把牛奶加热到约 60℃，海盐奶油最后加。"],
  },
];

const categories: Array<"全部" | Category> = ["全部", "招牌系列", "风味拿铁", "创意美式", "经典咖啡"];
const assetBase = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

export default function Home() {
  const [category, setCategory] = useState<(typeof categories)[number]>("全部");
  const [query, setQuery] = useState("");
  const [selectedDrink, setSelectedDrink] = useState<Drink | null>(null);

  const filteredDrinks = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    return drinks.filter((drink) => {
      const categoryMatches = category === "全部" || drink.category === category;
      const queryMatches = !keyword || [drink.name, drink.english, drink.flavor, drink.note].join(" ").toLowerCase().includes(keyword);
      return categoryMatches && queryMatches;
    });
  }, [category, query]);

  function chooseRandomDrink() {
    const pool = filteredDrinks.length ? filteredDrinks : drinks;
    setSelectedDrink(pool[Math.floor(Math.random() * pool.length)]);
  }

  return (
    <main>
      <header className="site-header">
        <a className="brand" href="#top" aria-label="返回顶部">
          <span className="brand-mark"><Coffee aria-hidden="true" /></span>
          <span><strong>铲子的小蓝杯实验室</strong><small>家庭复刻 · 非官方</small></span>
        </a>
        <span className="update-pill">更新于 2026.09</span>
      </header>

      <section className="hero" id="top">
        <img className="hero-image" src={`${assetBase}/drinks-hero.png`} alt="生椰拿铁、橙香咖啡和花香奶咖组成的清爽饮品画面" />
        <div className="hero-shade" />
        <div className="hero-copy">
          <span className="eyebrow"><Sparkles aria-hidden="true" /> 21 杯咖啡家庭复刻</span>
          <h1>今天，<br />做什么喝？</h1>
          <p>只收录含咖啡的饮品，从当季风味拿铁到清爽果C美式，点一杯就能看到用量和步骤。</p>
          <Button className="random-button" size="lg" onClick={chooseRandomDrink}><Shuffle aria-hidden="true" /> 帮我抽一杯</Button>
        </div>
      </section>

      <section className="control-panel" aria-label="筛选饮品">
        <div className="search-box">
          <Search aria-hidden="true" />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜饮品、口味…" aria-label="搜索饮品" />
        </div>
        <div className="category-list" role="group" aria-label="饮品分类">
          {categories.map((item) => (
            <button className={category === item ? "category-chip active" : "category-chip"} key={item} type="button" onClick={() => setCategory(item)} aria-pressed={category === item}>{item}</button>
          ))}
        </div>
      </section>

      <section className="menu-section" aria-labelledby="menu-title">
        <div className="section-heading">
          <div><span className="section-kicker">DRINK INDEX</span><h2 id="menu-title">小蓝杯复刻清单</h2></div>
          <span className="result-count">{filteredDrinks.length} 杯</span>
        </div>
        {filteredDrinks.length ? (
          <div className="drink-grid">
            {filteredDrinks.map((drink, index) => (
              <button className="drink-card" key={drink.id} type="button" onClick={() => setSelectedDrink(drink)} style={{ "--drink-accent": drink.color, "--drink-tint": drink.tint } as CSSProperties} aria-label={`查看${drink.name}配方`}>
                <div className="card-topline"><span className={`availability ${drink.availability === "当季上新" ? "new" : ""}`}>{drink.availability}</span><span className="card-number">{String(index + 1).padStart(2, "0")}</span></div>
                <div className="drink-photo-wrap">
                  <img className="drink-photo" src={`${assetBase}/drinks/${drink.id}.webp`} alt={`${drink.name}无标识实物杯图`} loading="lazy" />
                </div>
                <div className="card-copy"><p>{drink.english}</p><h3>{drink.name}</h3><span className="flavor">{drink.flavor}</span><small>{drink.note}</small></div>
                <div className="card-meta"><span><Clock3 aria-hidden="true" />{drink.time}</span><span>{drink.difficulty}</span><ChevronRight aria-hidden="true" /></div>
              </button>
            ))}
          </div>
        ) : (
          <div className="empty-state"><Coffee aria-hidden="true" /><h3>这杯暂时没找到</h3><p>换个关键词，或者清空筛选再看看。</p><Button variant="outline" onClick={() => { setQuery(""); setCategory("全部"); }}>查看全部饮品</Button></div>
        )}
      </section>

      <section className="brew-note">
        <div className="brew-note-icon"><Droplets aria-hidden="true" /></div>
        <div><span className="section-kicker">先记住这一个比例</span><h2>没有咖啡机，也能复刻</h2><p>每份“双份浓缩 36ml”，都可以替换为 <strong>3g 冻干黑咖啡＋30ml 热水</strong>。先把咖啡放凉，再做果咖和气泡咖啡。</p></div>
      </section>

      <footer>
        <div className="footer-main">
          <div><strong>关于这份菜单</strong><p>本页只保留含咖啡的饮品。名称与在售信息整理自你提供的 2026 年 9 月菜单截图及公开资料；各城市、门店和时段可能不同，请以瑞幸 App 实际显示为准。配方是按公开风味描述换算的家庭复刻版，并非瑞幸官方配方。杯图参照菜单商品图重新制作并清除了品牌标识。</p></div>
          <div className="source-links" aria-label="资料来源">
            <a href="https://lkcoffee.com/" target="_blank" rel="noreferrer">瑞幸官网 <ArrowUpRight aria-hidden="true" /></a>
            <a href="https://socialbeta.com/campaign/27847" target="_blank" rel="noreferrer">2026 鲜切柠C系列 <ArrowUpRight aria-hidden="true" /></a>
            <a href="https://www.stheadline.com/realtime-china/3596717/" target="_blank" rel="noreferrer">乳酸菌美式回归 <ArrowUpRight aria-hidden="true" /></a>
            <a href="https://m.xiachufang.com/recipe/106856920/" target="_blank" rel="noreferrer">生椰拿铁复刻参考 <ArrowUpRight aria-hidden="true" /></a>
          </div>
        </div>
        <p className="footer-signature">给每个“今天喝什么”的瞬间 · 铲子整理</p>
      </footer>

      <Dialog open={Boolean(selectedDrink)} onOpenChange={(open) => !open && setSelectedDrink(null)}>
        {selectedDrink && (
          <DialogContent className="recipe-dialog" style={{ "--drink-accent": selectedDrink.color, "--drink-tint": selectedDrink.tint } as CSSProperties}>
            <div className="recipe-accent" />
            <div className="recipe-lead">
              <DialogHeader className="recipe-header">
                <div className="recipe-badges"><span>{selectedDrink.availability}</span><span>{selectedDrink.category}</span></div>
                <p className="recipe-english">{selectedDrink.english}</p>
                <DialogTitle>{selectedDrink.name}</DialogTitle>
                <DialogDescription>{selectedDrink.flavor} · {selectedDrink.note}</DialogDescription>
              </DialogHeader>
              <img className="recipe-photo" src={`${assetBase}/drinks/${selectedDrink.id}.webp`} alt={`${selectedDrink.name}无标识实物杯图`} />
            </div>
            <div className="quick-facts">
              <span>{selectedDrink.temperature === "冰" ? <Snowflake aria-hidden="true" /> : <ThermometerSun aria-hidden="true" />}{selectedDrink.temperature}</span>
              <span><Clock3 aria-hidden="true" />{selectedDrink.time}</span>
              <span><Sparkles aria-hidden="true" />{selectedDrink.difficulty}</span>
            </div>
            <div className="recipe-body">
              <section><h3><span>01</span> 准备这些</h3><ul className="ingredient-list">{selectedDrink.ingredients.map((ingredient) => <li key={ingredient}><Check aria-hidden="true" />{ingredient}</li>)}</ul></section>
              <section><h3><span>02</span> 开始制作</h3><ol className="step-list">{selectedDrink.steps.map((step, index) => <li key={step}><span>{index + 1}</span><p>{step}</p></li>)}</ol></section>
            </div>
            <section className="tips-box"><h3><Sparkles aria-hidden="true" /> 铲子的小提醒</h3>{selectedDrink.tips.map((tip) => <p key={tip}>{tip}</p>)}</section>
          </DialogContent>
        )}
      </Dialog>
    </main>
  );
}
