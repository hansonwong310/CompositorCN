#import <Foundation/Foundation.h>
#import <AppKit/AppKit.h>
#import <objc/runtime.h>

static NSDictionary<NSString *, NSString *> *g_dict = nil;

static void initDictionary(void) {
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        NSMutableDictionary *dict = [NSMutableDictionary dictionary];
        
        NSString *bundlePath = [[NSBundle mainBundle] pathForResource:@"Localizable" ofType:@"strings" inDirectory:@"zh-Hans.lproj"];
        if (bundlePath) {
            NSDictionary *fileDict = [NSDictionary dictionaryWithContentsOfFile:bundlePath];
            if (fileDict) {
                [dict addEntriesFromDictionary:fileDict];
            }
        }
        
        NSDictionary *specials = @{
            @"Untitled": @"未命名",
            @"Show Controls": @"显示变换控件",
            @"Auto Select": @"自动选择",
            @"Width": @"宽度",
            @"Height": @"高度",
            @"Scale": @"缩放",
            @"Resolution": @"分辨率",
            @"High quality": @"高品质 (两次立方)",
            @"Bilinear": @"两次线性",
            @"Nearest neighbor": @"邻近",
            @"Transparent canvas": @"透明画布",
            @"White canvas": @"白色画布",
            @"Black canvas": @"黑色画布",
            @"Pixels": @"像素",
            @"Inches": @"英寸",
            @"Centimeters": @"厘米",
            @"Millimeters": @"毫米",
            @"Point Sample": @"取样点",
            @"3 by 3 Average": @"3×3 平均",
            @"5 by 5 Average": @"5×5 平均",
            @"Magic": @"魔棒",
            @"Wand": @"魔棒",
            @"Object": @"对象选择",
            @"Freehand": @"自由套索",
            @"Polygonal": @"多边形",
            @"Rectangle": @"矩形",
            @"Ellipse": @"椭圆",
            @"New": @"新建选区",
            @"Add": @"添加到选区",
            @"Subtract": @"从选区减去",
            @"Expand": @"扩展",
            @"Contract": @"收缩",
            @"Feather": @"羽化",
            @"Tolerance": @"容差",
            @"Contiguous": @"连续",
            @"Anti-alias": @"消除锯齿",
            @"All Layers": @"所有图层",
            @"Sample All Layers": @"对所有图层取样",
            
            @"Gaussian Blur": @"高斯模糊",
            @"Motion Blur": @"动感模糊",
            @"Add Noise": @"添加杂色",
            @"Vignette": @"晕影",
            @"Bloom / Glow": @"辉光 / 发光",
            @"Dither": @"抖动",
            @"Scanlines": @"扫描线",
            @"Tonal Contrast": @"色调对比度",
            @"Lens Correction": @"镜头校正",
            @"Camera Raw Filter": @"Camera Raw 滤镜",
            @"Remove Background": @"移除背景",
            @"Content-Aware Fill": @"内容识别填充",
            
            @"Curves": @"曲线",
            @"Levels": @"色阶",
            @"Exposure": @"曝光度",
            @"Hue/Saturation": @"色相/饱和度",
            @"Gradient Map": @"渐变映射",
            @"Grain": @"颗粒",
            @"Black & White": @"黑白",
            @"Color Balance": @"色彩平衡",
            
            @"Normal": @"正常",
            @"Darken": @"变暗",
            @"Multiply": @"正片叠底",
            @"Color Burn": @"颜色加深",
            @"Linear Burn": @"线性加深",
            @"Lighten": @"变亮",
            @"Screen": @"滤色",
            @"Color Dodge": @"颜色减淡",
            @"Linear Dodge (Add)": @"线性减淡 (添加)",
            @"Overlay": @"叠加",
            @"Soft Light": @"柔光",
            @"Hard Light": @"强光",
            @"Vivid Light": @"亮光",
            @"Linear Light": @"线性光",
            @"Pin Light": @"点光",
            @"Hard Mix": @"实色混合",
            @"Difference": @"差值",
            @"Exclusion": @"排除",
            @"Divide": @"划分",
            @"Hue": @"色相",
            @"Saturation": @"饱和度",
            @"Color": @"颜色",
            @"Luminosity": @"明度",

            @"File": @"文件",
            @"Edit": @"编辑",
            @"Image": @"图像",
            @"Layer": @"图层",
            @"Select": @"选择",
            @"Filter": @"滤镜",
            @"View": @"视图",
            @"Window": @"窗口",
            @"Help": @"帮助",
            @"Show": @"显示",
            @"Snap To": @"对齐到",
            @"Open Recent": @"最近打开",
            @"New Adjustment Layer": @"新建调整图层"
        };
        [dict addEntriesFromDictionary:specials];
        g_dict = [dict copy];
    });
}

static NSString *translateString(NSString *orig) {
    if (!orig || orig.length == 0) return orig;
    initDictionary();
    
    NSString *direct = g_dict[orig];
    if (direct) return direct;
    
    if ([orig hasSuffix:@"…"]) {
        NSString *base = [orig substringToIndex:orig.length - 1];
        NSString *trans = g_dict[base];
        if (trans) return [trans stringByAppendingString:@"…"];
    } else if ([orig hasSuffix:@"..."]) {
        NSString *base = [orig substringToIndex:orig.length - 3];
        NSString *trans = g_dict[base];
        if (trans) return [trans stringByAppendingString:@"…"];
    }
    
    if ([orig hasPrefix:@"Undo "]) {
        NSString *action = [orig substringFromIndex:5];
        NSString *transAction = translateString(action);
        return [NSString stringWithFormat:@"撤销 %@", transAction];
    }
    if ([orig hasPrefix:@"Redo "]) {
        NSString *action = [orig substringFromIndex:5];
        NSString *transAction = translateString(action);
        return [NSString stringWithFormat:@"重做 %@", transAction];
    }
    
    if ([orig containsString:@" · "]) {
        NSArray *parts = [orig componentsSeparatedByString:@" · "];
        NSMutableArray *transParts = [NSMutableArray arrayWithCapacity:parts.count];
        for (NSString *p in parts) {
            [transParts addObject:translateString(p)];
        }
        return [transParts componentsJoinedByString:@" · "];
    }
    
    return orig;
}

static void swizzleInstanceMethod(Class cls, SEL orig, SEL swiz) {
    Method mOrig = class_getInstanceMethod(cls, orig);
    Method mSwiz = class_getInstanceMethod(cls, swiz);
    if (mOrig && mSwiz) {
        method_exchangeImplementations(mOrig, mSwiz);
    }
}

@interface NSMenuItem (CompositorZH)
@end

@implementation NSMenuItem (CompositorZH)
- (instancetype)zh_initWithTitle:(NSString *)string action:(SEL)selector keyEquivalent:(NSString *)charCode {
    return [self zh_initWithTitle:translateString(string) action:selector keyEquivalent:charCode];
}
- (void)zh_setTitle:(NSString *)title {
    [self zh_setTitle:translateString(title)];
}
@end

@interface NSMenu (CompositorZH)
@end

@implementation NSMenu (CompositorZH)
- (instancetype)zh_initWithTitle:(NSString *)title {
    return [self zh_initWithTitle:translateString(title)];
}
- (void)zh_setTitle:(NSString *)title {
    [self zh_setTitle:translateString(title)];
}
- (NSMenuItem *)zh_addItemWithTitle:(NSString *)string action:(SEL)selector keyEquivalent:(NSString *)charCode {
    return [self zh_addItemWithTitle:translateString(string) action:selector keyEquivalent:charCode];
}
- (NSMenuItem *)zh_insertItemWithTitle:(NSString *)string action:(SEL)selector keyEquivalent:(NSString *)charCode atIndex:(NSInteger)index {
    return [self zh_insertItemWithTitle:translateString(string) action:selector keyEquivalent:charCode atIndex:index];
}
@end

@interface NSSegmentedControl (CompositorZH)
@end

@implementation NSSegmentedControl (CompositorZH)
- (void)zh_setLabel:(NSString *)label forSegment:(NSInteger)segment {
    [self zh_setLabel:translateString(label) forSegment:segment];
}
@end

@interface NSCell (CompositorZH)
@end

@implementation NSCell (CompositorZH)
- (void)zh_setTitle:(NSString *)title {
    [self zh_setTitle:translateString(title)];
}
- (void)zh_setStringValue:(NSString *)stringValue {
    [self zh_setStringValue:translateString(stringValue)];
}
@end

@interface NSButton (CompositorZH)
@end

@implementation NSButton (CompositorZH)
- (void)zh_setTitle:(NSString *)title {
    [self zh_setTitle:translateString(title)];
}
@end

@interface NSTextField (CompositorZH)
@end

@implementation NSTextField (CompositorZH)
- (void)zh_setStringValue:(NSString *)stringValue {
    [self zh_setStringValue:translateString(stringValue)];
}
@end

__attribute__((constructor))
static void initCompositorZH(void) {
    @autoreleasepool {
        initDictionary();
        
        swizzleInstanceMethod([NSMenuItem class], @selector(initWithTitle:action:keyEquivalent:), @selector(zh_initWithTitle:action:keyEquivalent:));
        swizzleInstanceMethod([NSMenuItem class], @selector(setTitle:), @selector(zh_setTitle:));
        
        swizzleInstanceMethod([NSMenu class], @selector(initWithTitle:), @selector(zh_initWithTitle:));
        swizzleInstanceMethod([NSMenu class], @selector(setTitle:), @selector(zh_setTitle:));
        swizzleInstanceMethod([NSMenu class], @selector(addItemWithTitle:action:keyEquivalent:), @selector(zh_addItemWithTitle:action:keyEquivalent:));
        swizzleInstanceMethod([NSMenu class], @selector(insertItemWithTitle:action:keyEquivalent:atIndex:), @selector(zh_insertItemWithTitle:action:keyEquivalent:atIndex:));
        
        swizzleInstanceMethod([NSSegmentedControl class], @selector(setLabel:forSegment:), @selector(zh_setLabel:forSegment:));
        
        swizzleInstanceMethod([NSCell class], @selector(setTitle:), @selector(zh_setTitle:));
        swizzleInstanceMethod([NSCell class], @selector(setStringValue:), @selector(zh_setStringValue:));
        
        swizzleInstanceMethod([NSButton class], @selector(setTitle:), @selector(zh_setTitle:));
        swizzleInstanceMethod([NSControl class], @selector(setStringValue:), @selector(zh_setStringValue:));
    }
}
