#import <Foundation/Foundation.h>
#import <AppKit/AppKit.h>
#import <objc/runtime.h>

static NSDictionary<NSString *, NSString *> *g_dict = nil;

static void loadDictionary(void) {
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
            @"Rectangle": @"矩形",
            @"Ellipse": @"椭圆",
            @"Freehand": @"自由套索",
            @"Polygonal": @"多边形",
            @"Wand": @"魔棒",
            @"Object": @"对象选择",
            @"Magic": @"魔棒",
            @"New": @"新建选区",
            @"Add": @"添加到选区",
            @"Subtract": @"从选区减去",
            @"Show Controls": @"显示变换控件",
            @"Auto Select": @"自动选择",
            @"Expand": @"扩展",
            @"New Canvas": @"新建画布",
            @"Brush Stroke": @"画笔描边",
            @"Move Layer": @"移动图层",
            @"Transform": @"自由变换",
            @"Crop": @"裁剪",
            @"Lasso": @"套索",
            @"Pan": @"抓手平移",
            @"Zoom": @"缩放"
        };
        [dict addEntriesFromDictionary:specials];
        g_dict = [dict copy];
    });
}

static NSString *translateString(NSString *orig) {
    if (!orig || orig.length == 0) return orig;
    loadDictionary();
    
    NSString *val = g_dict[orig];
    if (val) return val;
    
    if ([orig hasPrefix:@"Undo "]) {
        NSString *action = [orig substringFromIndex:5];
        NSString *transAction = g_dict[action] ?: action;
        return [NSString stringWithFormat:@"撤销 %@", transAction];
    }
    if ([orig hasPrefix:@"Redo "]) {
        NSString *action = [orig substringFromIndex:5];
        NSString *transAction = g_dict[action] ?: action;
        return [NSString stringWithFormat:@"重做 %@", transAction];
    }
    
    return orig;
}

@interface NSSegmentedControl (ZH)
@end

@implementation NSSegmentedControl (ZH)
- (void)zh_setLabel:(NSString *)label forSegment:(NSInteger)segment {
    NSString *zh = translateString(label);
    [self zh_setLabel:zh forSegment:segment];
}
@end

@interface NSMenuItem (ZH)
@end

@implementation NSMenuItem (ZH)
- (void)zh_setTitle:(NSString *)title {
    NSString *zh = translateString(title);
    [self zh_setTitle:zh];
}
@end

@interface NSButton (ZH)
@end

@implementation NSButton (ZH)
- (void)zh_setTitle:(NSString *)title {
    NSString *zh = translateString(title);
    [self zh_setTitle:zh];
}
@end

@interface NSTextField (ZH)
@end

@implementation NSTextField (ZH)
- (void)zh_setStringValue:(NSString *)stringValue {
    NSString *zh = translateString(stringValue);
    [self zh_setStringValue:zh];
}
@end

static void swizzle(Class cls, SEL orig, SEL swiz) {
    Method mOrig = class_getInstanceMethod(cls, orig);
    Method mSwiz = class_getInstanceMethod(cls, swiz);
    if (mOrig && mSwiz) {
        method_exchangeImplementations(mOrig, mSwiz);
    }
}

__attribute__((constructor))
static void initPlugin(void) {
    @autoreleasepool {
        loadDictionary();
        swizzle([NSSegmentedControl class], @selector(setLabel:forSegment:), @selector(zh_setLabel:forSegment:));
        swizzle([NSMenuItem class], @selector(setTitle:), @selector(zh_setTitle:));
        swizzle([NSButton class], @selector(setTitle:), @selector(zh_setTitle:));
        swizzle([NSTextField class], @selector(setStringValue:), @selector(zh_setStringValue:));
    }
}
