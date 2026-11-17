const assert = require('node:assert/strict');
const test = require('node:test');
const {createPolicy, advance} = require('../PresencePolicy.js');
const config = {enabled: true, awaySeconds: 15, faceEnabled: true};
const present = {state:'present', confidence:100, distance_mm:450};
const absent = {state:'absent', confidence:0, distance_mm:0};
function machine() {
    let p = createPolicy();
    return (time, sample, locked = false, options = config) => {
        const result = advance(p, time, sample, locked, options);
        p = result.policy;
        return result.actions;
    };
}
test('locks once after fifteen seconds of confirmed absence', () => {
    const run = machine(); run(0,present);
    for(let t=1000;t<16000;t+=1000) assert(!run(t,absent).includes('lock'));
    assert(run(16000,absent).includes('lock'));
    assert(!run(17000,absent).includes('lock'));
});
test('changing the away delay changes the actual deadline', () => {
    const run=machine(), settings={...config,awaySeconds:30};run(0,present,false,settings);
    for(let t=1000;t<31000;t+=1000)assert(!run(t,absent,false,settings).includes('lock'));
    assert(run(31000,absent,false,settings).includes('lock'));
});
test('return requests authentication exactly once and never unlocks', () => {
    const run=machine();run(0,present,true);run(1000,absent,true);run(3000,absent,true);
    assert.deepEqual(run(4000,present,true),['authenticate']);
    assert.deepEqual(run(5000,present,true),[]);
});
test('manual lock while seated is not immediately undone', () => {
    const run=machine();run(0,present);
    assert.deepEqual(run(1000,present,true),[]);
});
test('short absence does not count as walking away', () => {
    const run=machine();run(0,present,true);run(1000,absent,true);
    assert(!run(2000,present,true).includes('authenticate'));
});
test('transitional low-confidence reading does not spend arrival', () => {
    const run=machine();run(0,present,true);run(1000,absent,true);run(3000,absent,true);
    assert(!run(4000,{...present,confidence:10,distance_mm:1500},true).includes('authenticate'));
    assert(run(5000,present,true).includes('authenticate'));
});
test('initially absent or failed sensor cannot lock the desktop', () => {
    const run=machine();
    for(let t=0;t<40000;t+=1000) assert(!run(t,absent).includes('lock'));
});
test('stale readings and suspend cannot trigger a return', () => {
    const run=machine();run(0,present,true);run(1000,absent,true);run(3000,absent,true);
    assert(!run(9000,present,true).includes('authenticate'));
});
test('sensor failure cancels deadlines and camera scans', () => {
    const run=machine();run(0,present);run(1000,absent);run(3000,absent);
    assert(run(4000,{state:'unknown'}).includes('cancelFace'));
    for(let t=5000;t<30000;t+=1000)assert(!run(t,absent).includes('lock'));
});
test('return before deadline cancels automatic lock', () => {
    const run=machine();run(0,present);
    for(let t=1000;t<13000;t+=1000)run(t,absent);
    run(13000,present);
    assert(!run(16000,present).includes('lock'));
});
test('disabled face leaves away-lock available', () => {
    const run=machine(),settings={...config,faceEnabled:false};run(0,absent,true,settings);run(3000,absent,true,settings);
    assert(!run(4000,present,true,settings).includes('authenticate'));
});
test('disabled feature never acts', () => {
    const run=machine();
    for(let t=0;t<40000;t+=1000)assert.deepEqual(run(t,absent,false,{...config,enabled:false}),[]);
});
