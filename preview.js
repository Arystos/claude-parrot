#!/usr/bin/env node
// Preview the party parrot spinner animation in your terminal
// Usage: node preview.js          (ANSI art mode)
//        node preview.js --font   (PartyParrot.ttf font mode)

const ANSI_FRAMES = [
  " \x1b[38;2;180;102;101m\u2584\x1b[0m\x1b[38;2;204;114;114;48;2;219;123;122m\u2580\x1b[0m\x1b[38;2;142;99;91;48;2;211;125;122m\u2580\x1b[0m\x1b[38;2;130;82;78;48;2;160;92;91m\u2580\x1b[0m ",
  " \x1b[38;2;172;145;96;48;2;202;173;113m\u2580\x1b[0m\x1b[38;2;167;150;102;48;2;210;181;119m\u2580\x1b[0m\x1b[38;2;139;122;85;48;2;223;195;128m\u2580\x1b[0m\x1b[38;2;149;126;85m\u2584\x1b[0m ",
  "\x1b[38;2;93;163;93;48;2;84;146;84m\u2580\x1b[0m\x1b[38;2;110;192;109;48;2;125;223;125m\u2580\x1b[0m\x1b[38;2;89;132;85;48;2;126;221;125m\u2580\x1b[0m\x1b[38;2;119;211;119m\u2584\x1b[0m\x1b[38;2;80;139;80m\u2584\x1b[0m ",
  "\x1b[38;2;100;182;183;48;2;94;168;169m\u2580\x1b[0m\x1b[38;2;103;166;160;48;2;118;206;204m\u2580\x1b[0m\x1b[38;2;88;140;135;48;2;128;223;222m\u2580\x1b[0m\x1b[38;2;100;173;174m\u2584\x1b[0m  ",
  "\x1b[38;2;103;132;187;48;2;94;121;170m\u2580\x1b[0m\x1b[38;2;102;128;157;48;2;115;147;196m\u2580\x1b[0m\x1b[38;2;95;118;153;48;2;126;162;219m\u2580\x1b[0m\x1b[38;2;100;128;176m\u2584\x1b[0m  ",
  "\x1b[38;2;156;102;186;48;2;141;93;166m\u2580\x1b[0m\x1b[38;2;160;111;184;48;2;177;118;207m\u2580\x1b[0m\x1b[38;2;110;87;119;48;2;177;122;200m\u2580\x1b[0m\x1b[38;2;151;99;178m\u2584\x1b[0m  ",
  "\x1b[38;2;131;75;131m\u2584\x1b[0m\x1b[38;2;208;116;208;48;2;219;122;219m\u2580\x1b[0m\x1b[38;2;152;102;149;48;2;167;106;164m\u2580\x1b[0m\x1b[38;2;126;81;125;48;2;164;96;163m\u2580\x1b[0m  ",
  "\x1b[38;2;121;55;117m\u2584\x1b[0m\x1b[38;2;180;76;174m\u2584\x1b[0m\x1b[38;2;210;88;205;48;2;219;92;215m\u2580\x1b[0m\x1b[38;2;135;81;127;48;2;174;91;169m\u2580\x1b[0m\x1b[38;2;149;67;144m\u2584\x1b[0m ",
  " \x1b[38;2;170;74;123m\u2584\x1b[0m\x1b[38;2;206;90;155;48;2;215;93;160m\u2580\x1b[0m\x1b[38;2;142;82;108;48;2;198;94;148m\u2580\x1b[0m\x1b[38;2;91;61;72;48;2;157;74;115m\u2580\x1b[0m ",
  " \x1b[38;2;175;77;77m\u2584\x1b[0m\x1b[38;2;210;91;92;48;2;220;94;95m\u2580\x1b[0m\x1b[38;2;157;86;79;48;2;209;97;95m\u2580\x1b[0m\x1b[38;2;103;63;59;48;2;163;76;74m\u2580\x1b[0m ",
];

// PUA codepoints rendered by PartyParrot.ttf
const FONT_FRAMES = [
  "\uE000 ",  // frame 0
  "\uE001 ",  // frame 1
  "\uE002 ",  // frame 2
  "\uE003 ",  // frame 3
  "\uE004 ",  // frame 4
  "\uE005 ",  // frame 5
  "\uE006 ",  // frame 6
  "\uE007 ",  // frame 7
  "\uE008 ",  // frame 8
  "\uE009 ",  // frame 9
];

const VERBS = [
  "Thinking...", "Ruminating...", "Vibing...", "Clauding...",
  "Baking...", "Brewing...", "Pondering...", "Forging...",
  "Cooking...", "Crafting...",
];

var mode = process.argv.indexOf("--font") !== -1 ? "font" : "ansi";
var frames = mode === "font" ? FONT_FRAMES : ANSI_FRAMES;

var i = 0;
console.log("\n  Party Parrot Spinner Preview [" + mode + "] (Ctrl+C to exit)");
console.log("  Use --font to test PartyParrot.ttf codepoints\n");

setInterval(function () {
  process.stdout.write("\r  " + frames[i % frames.length] + " " + VERBS[i % VERBS.length] + "     ");
  i++;
}, 100);
