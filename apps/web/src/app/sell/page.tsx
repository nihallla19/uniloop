import Link from "next/link";

// Static form shell. Drafts, photo upload and publish wire up in Phase 3.
export default function SellPage() {
  return (
    <div className="page">
      <p className="eyebrow">Sell</p>
      <h1 className="display">Pass something on.</h1>
      <p className="note">
        Selling goes live with the listings API. Check what you can&apos;t sell on{" "}
        <Link href="/prohibited">Prohibited Items</Link>.
      </p>
      <form className="form">
        <fieldset className="fieldset">
          <legend>1. Photos</legend>
          <div className="field">
            <label htmlFor="photos">Up to 8 photos. The first one is the cover.</label>
            <input id="photos" type="file" accept="image/jpeg,image/png,image/webp" multiple />
          </div>
        </fieldset>
        <fieldset className="fieldset">
          <legend>2. About the item</legend>
          <div className="field">
            <label htmlFor="title">Title</label>
            <input id="title" maxLength={80} />
            <small>Example: Casio FX-991ES, used for one semester</small>
          </div>
          <div className="field">
            <label htmlFor="description">Description</label>
            <textarea id="description" maxLength={2000} />
            <small>Example: Works perfectly, small scratch on the cover. Comes with the case.</small>
          </div>
        </fieldset>
        <fieldset className="fieldset">
          <legend>3. Price</legend>
          <div className="row">
            <div className="field">
              <label htmlFor="mode">How are you selling?</label>
              <select id="mode">
                <option>Fixed price</option><option>Negotiable</option><option>Free</option><option>Swap</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="price">Price (₹)</label>
              <input id="price" inputMode="numeric" placeholder="650" />
            </div>
          </div>
          <div className="field">
            <label htmlFor="condition">Condition</label>
            <select id="condition">
              <option>New: never used</option>
              <option>Like new: used briefly, no visible wear</option>
              <option>Good: used, works well, minor wear</option>
              <option>Fair: visible wear, still works</option>
              <option>For parts: damaged or not fully working</option>
            </select>
          </div>
        </fieldset>
        <fieldset className="fieldset">
          <legend>4. Handover</legend>
          <div className="field">
            <label htmlFor="pickup">Pickup point</label>
            <select id="pickup"><option>Library entrance</option><option>Canteen</option><option>Main gate</option></select>
          </div>
          <div className="field">
            <label htmlFor="availability">When can you meet?</label>
            <input id="availability" maxLength={120} />
            <small>Example: Weekdays after 4 pm</small>
          </div>
        </fieldset>
        <div><button className="btn btn-solid" type="button" disabled>Publish (coming soon)</button></div>
      </form>
    </div>
  );
}
