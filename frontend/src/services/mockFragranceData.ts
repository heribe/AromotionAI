import type { FragranceSessionData, ChatMessage, ChatResponse, FragrancePlan } from '../types/fragrance';

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

const MOCK_PLANS: FragrancePlan[] = [
  {
    planId: 'plan-1',
    name: '粉色之梦',
    category: '花果甜香',
    topNotes: [
      { name: '佛手柑', description: '明亮清新的开场', reason: '呼应粉色系审美中的活力感' },
      { name: '粉红胡椒', description: '微辣的甜蜜点缀', reason: '匹配甜美系风格中的俏皮元素' }
    ],
    middleNotes: [
      { name: '鸢尾花', description: '粉质的优雅花香', reason: '连接古典系审美与蓝紫色偏好' },
      { name: '玫瑰', description: '经典的浪漫花香', reason: '呼应约会社交场景的浪漫需求' }
    ],
    baseNotes: [
      { name: '白麝香', description: '洁净柔软的贴肤感', reason: '延续整体的温柔知性基调' },
      { name: '雪松', description: '干燥的冷感木质', reason: '平衡前中调的甜美，提升高级感' }
    ],
    recommendationReason: '这款方案以“粉红胡椒+玫瑰”为核心，完美契合受众群体的浪漫感性特质。前调的明亮跳跃与中调的丰满花香共同营造出一种“出片率极高”的社交氛围，非常适合她们日常的约会与探店场景。',
    fragranceStory: '“她推开那扇复古咖啡馆的门，下午三点的阳光正好穿过蕾丝窗帘。指尖还残留着清晨切开的佛手柑香气，而丝绒长裙上则沾染了花园里刚剪下的玫瑰。她不经意间拂过长发，那是一抹隐秘而温柔的白麝香，像是对这个世界最柔软的抗议。”'
  },
  {
    planId: 'plan-2',
    name: '晨雾森林',
    category: '绿叶木质调',
    topNotes: [
      { name: '无花果叶', description: '带有奶香的绿意', reason: '提供一种不具攻击性的清新感' },
      { name: '苦橙叶', description: '微苦的枝干气息', reason: '增加自然氛围的真实感' }
    ],
    middleNotes: [
      { name: '绿茶', description: '清透悠远的茶香', reason: '契合日系文艺与安静内向的性格' },
      { name: '茉莉', description: '通透的白花香', reason: '为木质调中注入女性的柔美' }
    ],
    baseNotes: [
      { name: '檀木', description: '温润奶感的木质', reason: '提供持久的情绪安抚作用' },
      { name: '岩兰草', description: '带有泥土气息的根茎', reason: '带来极强的安全感与落地感' }
    ],
    recommendationReason: '这是一款为内向、敏锐人群设计的“情绪庇护所”。它没有强烈的社交扩张性，而是向内探索。檀木与绿茶的搭配能有效缓解现代生活中的焦虑，非常适合居家放松或是一人阅读的独处时光。',
    fragranceStory: '“那是雨后森林深处的一座木屋。空气中弥漫着被打湿的蕨类植物和无花果树叶的清苦。她在屋檐下泡了一壶绿茶，听着雨滴砸在木板上的声音。当檀木香炉里升起第一缕青烟时，整个世界都安静了下来。”'
  },
  {
    planId: 'plan-3',
    name: '琥珀幻夜',
    category: '东方美食调',
    topNotes: [
      { name: '粉红葡萄柚', description: '多汁的酸甜果香', reason: '用反差感开启沉闷的夜间社交' },
      { name: '藏红花', description: '带有皮革感的香料', reason: '彰显独立自信的个性宣言' }
    ],
    middleNotes: [
      { name: '晚香玉', description: '极具侵略性的白花', reason: '满足晚间派对中对回头率的需求' },
      { name: '可可果', description: '苦涩的黑巧克力', reason: '呼应烘焙美食的潜在兴趣' }
    ],
    baseNotes: [
      { name: '广藿香', description: '药感深沉的泥土', reason: '压制甜度，带来神秘复古感' },
      { name: '波旁香草', description: '醇厚的烟熏甜润', reason: '提供极致的情感价值和包裹感' }
    ],
    recommendationReason: '针对夜间社交和圈层派对设计的“战袍”。它大胆、华丽且充满张力。晚香玉的扩张力结合香草的诱惑，能完美满足受众在社交场合中“成为视觉与嗅觉焦点”的深层需求。',
    fragranceStory: '“午夜十二点，高跟鞋敲击在冰冷的大理石地面上。她是这场舞会上最神秘的来客。藏红花的辛辣与晚香玉的放肆交织在一起，就像她那抹化不开的烟熏红唇。当她离去，空气中只剩下广藿香和香草留下的暧昧余温，让人整夜难眠。”'
  }
];

const MOCK_SESSION_DATA: FragranceSessionData = {
  sessionId: 'session-001',
  taskId: 'task-001',
  selectedTags: {
    '气候-消费带': {
      '气候带': ['湿热南方'],
      '城市线级': ['一线/新一线', '二线']
    },
    '穿搭风格-香调映射': {
      '穿搭风格': ['法式优雅', '日系文艺'],
      '色彩偏好': ['莫兰迪色', '奶油白']
    }
  },
  recommendations: MOCK_PLANS,
  icebergAnalysis: {
    surface: '甜美系穿搭、粉色系偏好、圈层社交（同好会/茶会）、种草型消费路径，这些指向了一个高度视觉化、注重外在形象表达的用户群体。',
    middle: '情绪需求驱动的消费动机，拍照出片和约会社交的场景需求，反映了这个群体通过「穿搭-拍照-分享」的闭环来获得自我认同和社交认可。',
    deep: '在亚文化穿搭的表象下，是对「理想化自我」的持续构建。她们通过精致的外在包装来回应内心对美好、浪漫、被重视的渴望。'
  },
  status: 'active',
  createdAt: new Date().toISOString()
};

export const mockFragranceApi = {
  /** 获取初始 Session 数据 */
  async getSession(sessionId: string): Promise<FragranceSessionData> {
    await delay(600);
    return MOCK_SESSION_DATA;
  },

  /** 获取历史对话记录 */
  async getHistory(sessionId: string): Promise<{ messages: ChatMessage[] }> {
    await delay(300);
    return {
      messages: [
        {
          id: 'msg-0',
          role: 'assistant',
          content: '分析已完成。根据您选择的标签，我为您生成了 3 套初始香调方案。您可以随时在对话框告诉我修改意见。',
          updatedPlans: null,
          createdAt: new Date(Date.now() - 60000).toISOString(),
        }
      ]
    };
  },

  /** 与 AI 助手对话 */
  async chat(sessionId: string, message: string): Promise<ChatResponse> {
    await delay(1500); // 模拟大模型思考延迟

    // Mock: 演示方案一被修改的剧本
    if (message.includes('后调') && (message.includes('方案一') || message.includes('沉香') || message.includes('木'))) {
      const updatedPlan1 = { ...MOCK_PLANS[0] };
      updatedPlan1.baseNotes = [
        { name: '沉香', description: '深沉的东方木质', reason: '增加神秘感和深度', changed: true },
        { name: '乌木', description: '烟熏的暗色木质', reason: '与粉色系形成反差张力', changed: true }
      ];
      updatedPlan1.recommendationReason = '这款方案现在以“粉红胡椒+玫瑰”为核心，但在后调加入了沉香和乌木。这种强烈的反差打破了原本纯粹的甜美，赋予了作品更深的层次和“生人勿近”的冷冽感，非常适合希望在甜美中彰显个性的高阶用香者。';

      return {
        messageId: `msg-${Date.now()}`,
        reply: '好的，我理解你希望增加方案一的深度和层次感。我已将它的后调替换为深沉的东方木质（沉香与乌木）。这种与前中调花果香产生的反差，会让整体香气更具张力和神秘感。',
        updatedPlans: [updatedPlan1]
      };
    }

    // 默认回复
    return {
      messageId: `msg-${Date.now()}`,
      reply: `这是一个很好的想法！关于“${message}”，我们可以通过调整中调的花香比例，或者加入一些清新的柑橘类香材来实现。不过为了保持方案的完整性，你需要我具体修改哪一个方案呢？`,
      updatedPlans: null
    };
  }
};
